"""
Natural Language to SQL conversion engine.
Converts user questions into SQL queries using LLM with proper validation and caching.
"""
import hashlib
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
import re

from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langsmith import traceable
import pandas as pd

from config import settings
from database import db_manager, AppMetrics, QueryCache
from .query_validator import SQLValidator
from sqlalchemy import text

logger = logging.getLogger(__name__)


class SQLGenerationEngine:
    """
    Converts natural language queries to SQL using LLM.
    
    Features:
    - Smart SQL generation with context awareness
    - Query validation and sanitization
    - Caching for cost optimization
    - Error handling and user-friendly messages
    """
    
    def __init__(self):
        """Initialize the SQL generation engine."""
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.1,  # Low temperature for consistent SQL generation
            api_key=settings.openai_api_key
        )
        
        self.validator = SQLValidator()
        self._setup_prompts()
    
    def _setup_prompts(self):
        """Set up the prompt templates for SQL generation."""
        
        # Main SQL generation prompt
        self.sql_prompt = PromptTemplate(
            input_variables=["question", "schema_info", "sample_data"],
            template="""You are an expert SQL analyst for a mobile app analytics company called Rounds.

DATABASE SCHEMA:
{schema_info}

SAMPLE DATA (for context):
{sample_data}

IMPORTANT RULES:
1. Generate PostgreSQL-compatible SQL only
2. Use table name "app_metrics" (not AppMetrics)
3. Always include meaningful column aliases
4. For date ranges, assume current timeframe unless specified
5. For "popularity", use total installs as the metric
6. For revenue questions, sum both in_app_revenue and ads_revenue
7. Always use proper aggregation (SUM, COUNT, AVG, etc.)
8. Include ORDER BY for rankings and comparisons
9. Use LIMIT when showing "top" items
10. Handle case-sensitive app names properly

QUERY INTERPRETATION GUIDELINES:
- "How many apps" = COUNT(DISTINCT app_name)
- "Which apps" = List apps with relevant metrics
- "Revenue" = in_app_revenue + ads_revenue unless specified
- "Popularity" = Total installs
- "Performance" = Revenue or ROI depending on context
- Date comparisons should use explicit date ranges

USER QUESTION: {question}

CRITICAL: Return ONLY executable SQL. Do not include any explanations, comments, facts about companies, or additional text. Just pure SQL ending with a semicolon:"""
        )
        
        # Query classification prompt
        self.classification_prompt = PromptTemplate(
            input_variables=["question"],
            template="""Classify this user question about mobile app analytics:

Question: {question}

Categories:
1. SIMPLE_COUNT - Simple counting questions (how many apps, total installs)
2. SIMPLE_AGGREGATE - Basic aggregations (total revenue, average installs)
3. RANKING - Questions asking for top/best/worst items
4. COMPARISON - Comparing different periods, platforms, or countries
5. DETAILED_ANALYSIS - Complex multi-dimensional analysis
6. OFF_TOPIC - Questions not related to app analytics
7. EXPORT_REQUEST - User asking to export data as CSV
8. SQL_REQUEST - User asking to see the SQL query

Respond with just the category name:"""
        )
    
    def _get_schema_info(self) -> str:
        """Get database schema information for the prompt."""
        return """
Table: app_metrics
Columns:
- id (integer, primary key)
- app_name (string) - Name of the mobile app (e.g., 'TikTok', 'Instagram')
- platform (string) - 'iOS' or 'Android'
- date (date) - Date of the metrics (YYYY-MM-DD format)
- country (string) - 3-letter country code (e.g., 'USA', 'GBR')
- installs (integer) - Number of app downloads
- in_app_revenue (decimal) - Revenue from in-app purchases
- ads_revenue (decimal) - Revenue from advertisements
- ua_cost (decimal) - User acquisition cost

Available apps: TikTok, Instagram, WhatsApp, Facebook, YouTube, Snapchat, Twitter, LinkedIn, Pinterest, Reddit, Spotify, Netflix, Amazon, Uber, Airbnb, Discord, Twitch, Duolingo, Zoom, PayPal

Available countries: USA, GBR, DEU, FRA, JPN, KOR, CHN, IND, BRA, CAN, AUS, ESP, ITA, NLD, SWE
"""
    
    def _get_sample_data(self) -> str:
        """Get sample data for context."""
        return """
Example rows:
- TikTok, iOS, 2024-01-15, USA, 15000 installs, $25000 in-app revenue, $8000 ads revenue, $45000 UA cost
- Instagram, Android, 2024-01-15, GBR, 12000 installs, $18000 in-app revenue, $6000 ads revenue, $30000 UA cost
"""
    
    def _hash_query(self, question: str) -> str:
        """Generate a hash for the query for caching."""
        return hashlib.sha256(question.lower().strip().encode()).hexdigest()
    
    @traceable(name="classify_query")
    def classify_query(self, question: str) -> str:
        """
        Classify the type of user question.
        
        Args:
            question: User's natural language question
            
        Returns:
            Query classification category
        """
        try:
            chain = self.classification_prompt | self.llm | StrOutputParser()
            classification = chain.invoke({"question": question})
            return classification.strip()
        except Exception as e:
            logger.error(f"Failed to classify query: {e}")
            return "DETAILED_ANALYSIS"  # Default to most comprehensive
    
    def _check_cache(self, question: str) -> Optional[Dict[str, Any]]:
        """Check if query result is cached."""
        query_hash = self._hash_query(question)
        
        with db_manager.get_session() as session:
            cached = session.query(QueryCache).filter(
                QueryCache.query_hash == query_hash
            ).first()
            
            if cached:
                # Update access tracking
                cached.access_count += 1
                cached.last_accessed = pd.Timestamp.now()
                session.commit()
                
                return {
                    "sql_query": cached.sql_query,
                    "result_data": json.loads(cached.result_data) if cached.result_data else None,
                    "result_count": cached.result_count,
                    "from_cache": True
                }
        
        return None
    
    def _save_to_cache(self, question: str, sql_query: str, 
                      result_data: Any, result_count: int):
        """Save query result to cache."""
        query_hash = self._hash_query(question)
        
        with db_manager.get_session() as session:
            # Check if already exists
            existing = session.query(QueryCache).filter(
                QueryCache.query_hash == query_hash
            ).first()
            
            if existing:
                # Update existing
                existing.sql_query = sql_query
                existing.result_data = json.dumps(result_data, default=str)
                existing.result_count = result_count
                existing.last_accessed = pd.Timestamp.now()
                existing.access_count += 1
            else:
                # Create new
                cache_entry = QueryCache(
                    query_hash=query_hash,
                    natural_language_query=question,
                    sql_query=sql_query,
                    result_data=json.dumps(result_data, default=str),
                    result_count=result_count
                )
                session.add(cache_entry)
            
            session.commit()
    
    @traceable(name="generate_sql")
    def generate_sql(self, question: str) -> str:
        """
        Generate SQL query from natural language question.
        
        Args:
            question: User's natural language question
            
        Returns:
            Generated SQL query
            
        Raises:
            ValueError: If SQL generation fails or query is invalid
        """
        try:
            # Set up the chain
            chain = self.sql_prompt | self.llm | StrOutputParser()
            
            # Generate SQL
            sql_query = chain.invoke({
                "question": question,
                "schema_info": self._get_schema_info(),
                "sample_data": self._get_sample_data()
            })
            
            # Clean up the SQL
            sql_query = sql_query.strip()
            
            # Remove any markdown formatting that might have been added
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'\n?```', '', sql_query)
            
            # Validate the SQL
            validation_result = self.validator.validate_sql(sql_query)
            if not validation_result["is_valid"]:
                raise ValueError(f"Generated SQL is invalid: {validation_result['error']}")
            
            logger.info(f"Generated SQL: {sql_query}")
            return sql_query
            
        except Exception as e:
            logger.error(f"Failed to generate SQL: {e}")
            raise ValueError(f"Could not generate SQL for your question: {str(e)}")
    
    @traceable(name="execute_sql_query")
    def execute_sql(self, sql_query: str) -> Tuple[List[Dict], int]:
        """
        Execute SQL query and return results.
        
        Args:
            sql_query: SQL query to execute
            
        Returns:
            Tuple of (results as list of dicts, result count)
            
        Raises:
            Exception: If query execution fails
        """
        try:
            with db_manager.get_session() as session:
                result = session.execute(text(sql_query))
                
                # Convert to list of dictionaries
                columns = result.keys()
                rows = result.fetchall()
                
                results = [dict(zip(columns, row)) for row in rows]
                
                logger.info(f"Query executed successfully, returned {len(results)} rows")
                return results, len(results)
                
        except Exception as e:
            logger.error(f"Failed to execute SQL: {e}")
            raise Exception(f"Failed to execute query: {str(e)}")
    
    @traceable(name="process_natural_language_query")
    def process_query(self, question: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Process a natural language query end-to-end.
        
        Args:
            question: User's natural language question
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary containing query results and metadata
        """
        try:
            # Check cache first if enabled
            if use_cache:
                cached_result = self._check_cache(question)
                if cached_result:
                    logger.info("Returning cached result")
                    return cached_result
            
            # Classify the query
            query_type = self.classify_query(question)
            
            # Handle off-topic questions
            if query_type == "OFF_TOPIC":
                logger.info(f"Question classified as off-topic: {question}")
                return {
                    "success": False,
                    "error": "off_topic",
                    "message": "I'm focused on helping with app analytics. Please ask questions about app performance, installs, revenue, or user acquisition costs.",
                    "query_type": query_type,
                    "suggestions": [
                        "How many apps do we have?",
                        "Which platform performs better?", 
                        "Show me revenue by country",
                        "What are our top apps by installs?"
                    ]
                }
            
            # Generate SQL for analytics questions
            sql_query = self.generate_sql(question)
            
            # Execute SQL
            results, result_count = self.execute_sql(sql_query)
            
            # Save to cache
            self._save_to_cache(question, sql_query, results, result_count)
            
            return {
                "sql_query": sql_query,
                "result_data": results,
                "result_count": result_count,
                "query_type": query_type,
                "from_cache": False
            }
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            raise
    
    def is_app_analytics_question(self, question: str) -> bool:
        """
        Determine if a question is related to app analytics.
        
        Args:
            question: User's question
            
        Returns:
            True if question is app analytics related, False otherwise
        """
        # Keywords that indicate app analytics questions
        app_keywords = [
            "app", "apps", "install", "installs", "revenue", "download",
            "user", "users", "platform", "ios", "android", "country",
            "analytics", "metrics", "performance", "tiktok", "instagram",
            "facebook", "youtube", "snapchat", "advertising", "ads"
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in app_keywords)


# Global instance
sql_engine = SQLGenerationEngine() 
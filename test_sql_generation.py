#!/usr/bin/env python3
"""
Test script to debug SQL generation issues.
"""
import os
from dotenv import load_dotenv
load_dotenv()

from ai.sql_engine import SQLGenerationEngine
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from config import settings
import re

def test_full_sql_generation():
    """Test full SQL generation with validation."""
    
    print("🧪 Testing Full SQL Generation (With Validation)...")
    print("-" * 60)
    
    engine = SQLGenerationEngine()
    
    test_questions = [
        "How many apps do we have?",
        "What's our total revenue?", 
        "Show me all apps sorted by installs",
    ]
    
    for question in test_questions:
        print(f"\n📝 Question: {question}")
        try:
            sql = engine.generate_sql(question)
            print(f"✅ Generated SQL: {sql}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "-" * 60)

def test_raw_sql_generation():
    """Test raw SQL generation without validation."""
    
    print("🧪 Testing Raw SQL Generation (No Validation)...")
    print("-" * 60)
    
    # Create LLM directly
    llm = ChatOpenAI(
        model=settings.openai_model,
        temperature=0.1,
        api_key=settings.openai_api_key
    )
    
    # Use the same prompt from the engine
    sql_prompt = PromptTemplate(
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

Generate ONLY the SQL query (no explanations, no markdown formatting):"""
    )
    
    # Get schema info
    schema_info = """
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

Available apps: TikTok, Instagram, WhatsApp, Facebook, YouTube
Available countries: USA, GBR, DEU, FRA, JPN, KOR, CHN, IND, BRA, CAN, AUS, ESP, ITA, NLD, SWE
"""
    
    sample_data = """
Example rows:
- TikTok, iOS, 2024-01-15, USA, 15000 installs, $25000 in-app revenue, $8000 ads revenue, $45000 UA cost
- Instagram, Android, 2024-01-15, GBR, 12000 installs, $18000 in-app revenue, $6000 ads revenue, $30000 UA cost
"""
    
    test_questions = [
        "How many apps do we have?",
        "What's our total revenue?", 
        "Show me all apps sorted by installs",
    ]
    
    chain = sql_prompt | llm | StrOutputParser()
    
    for question in test_questions:
        print(f"\n📝 Question: {question}")
        try:
            raw_sql = chain.invoke({
                "question": question,
                "schema_info": schema_info,
                "sample_data": sample_data
            })
            
            # Clean up the SQL
            sql_query = raw_sql.strip()
            sql_query = re.sub(r'```sql\n?', '', sql_query)
            sql_query = re.sub(r'\n?```', '', sql_query)
            
            print(f"🔍 Raw SQL: {sql_query}")
            
            # Check if it contains app_metrics
            if "app_metrics" in sql_query.lower():
                print("✅ Contains app_metrics table")
            else:
                print("❌ Missing app_metrics table!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "-" * 60)

if __name__ == "__main__":
    print("=" * 80)
    test_full_sql_generation()
    print("\n" + "=" * 80)
    test_raw_sql_generation() 
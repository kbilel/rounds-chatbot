"""
Response formatting for the Slack chatbot.
Determines appropriate response format and creates user-friendly messages.
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
import pandas as pd

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """
    Formats query results into appropriate response formats.
    
    Features:
    - Smart decision making between simple vs detailed responses
    - Table formatting for Slack
    - Human-friendly explanations
    - Context-aware assumptions documentation
    """
    
    def __init__(self):
        """Initialize the response formatter."""
        self.max_simple_response_rows = 1
        self.max_table_rows = 20
        self.decimal_places = 2
    
    def _format_currency(self, amount: float) -> str:
        """Format a number as currency."""
        if amount >= 1_000_000:
            return f"${amount/1_000_000:.1f}M"
        elif amount >= 1_000:
            return f"${amount/1_000:.1f}K"
        else:
            return f"${amount:.2f}"
    
    def _format_number(self, number: int) -> str:
        """Format a large number with appropriate suffixes."""
        if number >= 1_000_000:
            return f"{number/1_000_000:.1f}M"
        elif number >= 1_000:
            return f"{number/1_000:.1f}K"
        else:
            return f"{number:,}"
    
    def _should_use_simple_format(self, query_type: str, result_count: int, 
                                 question: str) -> bool:
        """
        Determine if response should use simple format.
        
        Args:
            query_type: Type of query (SIMPLE_COUNT, RANKING, etc.)
            result_count: Number of result rows
            question: Original user question
            
        Returns:
            True if simple format should be used
        """
        # Always use simple format for these query types
        simple_query_types = {"SIMPLE_COUNT", "SIMPLE_AGGREGATE"}
        if query_type in simple_query_types:
            return True
        
        # Use simple format for single-row results
        if result_count <= self.max_simple_response_rows:
            return True
        
        # Check question patterns that suggest simple answers
        simple_patterns = [
            "how many", "total", "average", "what is", "what's"
        ]
        question_lower = question.lower()
        if any(pattern in question_lower for pattern in simple_patterns):
            return True
        
        return False
    
    def _create_simple_response(self, results: List[Dict], question: str,
                              query_type: str) -> str:
        """
        Create a simple text response for straightforward questions.
        
        Args:
            results: Query results
            question: Original question
            query_type: Type of query
            
        Returns:
            Simple text response
        """
        if not results:
            return "No data found for your query."
        
        result = results[0]
        question_lower = question.lower()
        
        # Handle different types of simple responses
        if "how many apps" in question_lower:
            count = result.get('number_of_apps', result.get('total_apps', result.get('count', result.get('app_count', 0))))
            return f"We have **{count} apps** in our portfolio."
        
        elif "how many" in question_lower and "ios" in question_lower:
            count = result.get('number_of_apps', result.get('total_apps', result.get('count', result.get('app_count', 0))))
            return f"We have **{count} iOS apps** in our portfolio."
        
        elif "how many" in question_lower and "android" in question_lower:
            count = result.get('number_of_apps', result.get('total_apps', result.get('count', result.get('app_count', 0))))
            return f"We have **{count} Android apps** in our portfolio."
        
        elif "total revenue" in question_lower:
            revenue = result.get('total_revenue', 0)
            return f"Total revenue: **{self._format_currency(float(revenue))}**"
        
        elif "total installs" in question_lower:
            installs = result.get('total_installs', 0)
            return f"Total installs: **{self._format_number(int(installs))}**"
        
        elif "average" in question_lower:
            # Find the first numeric column for average
            for key, value in result.items():
                if isinstance(value, (int, float, Decimal)) and value > 0:
                    if "revenue" in key:
                        return f"Average {key.replace('_', ' ')}: **{self._format_currency(float(value))}**"
                    elif "install" in key:
                        return f"Average {key.replace('_', ' ')}: **{self._format_number(int(value))}**"
                    else:
                        return f"Average {key.replace('_', ' ')}: **{value:.2f}**"
        
        # Default simple response for single results
        response_parts = []
        for key, value in result.items():
            if isinstance(value, (int, float, Decimal)):
                if "revenue" in key.lower():
                    response_parts.append(f"{key.replace('_', ' ').title()}: {self._format_currency(float(value))}")
                elif "install" in key.lower():
                    response_parts.append(f"{key.replace('_', ' ').title()}: {self._format_number(int(value))}")
                else:
                    response_parts.append(f"{key.replace('_', ' ').title()}: {value}")
            else:
                response_parts.append(f"{key.replace('_', ' ').title()}: {value}")
        
        return "**" + " | ".join(response_parts) + "**"
    
    def _create_table_response(self, results: List[Dict], question: str,
                             query_type: str) -> str:
        """
        Create a formatted table response for complex queries.
        
        Args:
            results: Query results
            question: Original question
            query_type: Type of query
            
        Returns:
            Formatted table response with explanation
        """
        if not results:
            return "No data found for your query."
        
        # Limit results if too many
        limited_results = results[:self.max_table_rows]
        
        # Convert to DataFrame for easier formatting
        df = pd.DataFrame(limited_results)
        
        # Format numeric columns
        for col in df.columns:
            if df[col].dtype in ['int64', 'float64']:
                if 'revenue' in col.lower() or 'cost' in col.lower():
                    df[col] = df[col].apply(lambda x: self._format_currency(float(x)) if pd.notna(x) else 'N/A')
                elif 'install' in col.lower():
                    df[col] = df[col].apply(lambda x: self._format_number(int(x)) if pd.notna(x) else 'N/A')
                else:
                    df[col] = df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else 'N/A')
        
        # Create table header
        headers = [col.replace('_', ' ').title() for col in df.columns]
        
        # Create table rows
        table_lines = []
        table_lines.append("| " + " | ".join(headers) + " |")
        table_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        
        for _, row in df.iterrows():
            row_data = [str(val) for val in row.values]
            table_lines.append("| " + " | ".join(row_data) + " |")
        
        table = "\n".join(table_lines)
        
        # Add explanation based on query type
        explanation = self._generate_explanation(question, query_type, len(results), limited_results)
        
        # Combine table and explanation
        response = f"{explanation}\n\n{table}"
        
        # Add truncation notice if needed
        if len(results) > self.max_table_rows:
            response += f"\n\n*Showing top {self.max_table_rows} results out of {len(results)} total.*"
        
        return response
    
    def _generate_explanation(self, question: str, query_type: str, 
                            total_results: int, sample_results: List[Dict]) -> str:
        """
        Generate an explanation for the query results.
        
        Args:
            question: Original question
            query_type: Type of query
            total_results: Total number of results
            sample_results: Sample of results for context
            
        Returns:
            Explanation text
        """
        question_lower = question.lower()
        
        # Query-specific explanations
        if "popularity" in question_lower:
            return "📊 **App Popularity Ranking** (based on total installs across all platforms and countries)"
        
        elif "revenue" in question_lower and "country" in question_lower:
            return "💰 **Revenue by Country** (includes both in-app purchases and advertising revenue)"
        
        elif "top" in question_lower or "best" in question_lower:
            return f"🏆 **Top Performers** (showing the highest ranked items based on your criteria)"
        
        elif "comparison" in question_lower or "compare" in question_lower:
            return "⚖️ **Comparison Analysis** (side-by-side metrics for the requested comparison)"
        
        elif query_type == "RANKING":
            return "📈 **Ranking Results** (ordered by performance metrics)"
        
        elif query_type == "DETAILED_ANALYSIS":
            return "🔍 **Detailed Analysis** (comprehensive breakdown of your requested metrics)"
        
        # Default explanation based on data characteristics
        if total_results == 1:
            return "📋 **Query Result**"
        elif total_results <= 5:
            return f"📋 **Query Results** ({total_results} items found)"
        else:
            return f"📋 **Query Results** ({total_results} items found)"
    
    def _add_assumptions(self, question: str, results: List[Dict]) -> str:
        """
        Add assumptions made during query processing.
        
        Args:
            question: Original question
            results: Query results
            
        Returns:
            Assumptions text
        """
        assumptions = []
        question_lower = question.lower()
        
        # Time-based assumptions
        if "recent" in question_lower or "latest" in question_lower:
            assumptions.append("• Using the most recent available data")
        elif not any(time_word in question_lower for time_word in ['day', 'week', 'month', 'year', 'date']):
            assumptions.append("• Including data from all available time periods")
        
        # Platform assumptions
        if not any(platform in question_lower for platform in ['ios', 'android', 'platform']):
            assumptions.append("• Including both iOS and Android platforms")
        
        # Geographic assumptions
        if not any(geo_word in question_lower for geo_word in ['country', 'usa', 'europe', 'asia']):
            assumptions.append("• Including data from all countries")
        
        # Revenue assumptions
        if "revenue" in question_lower and not ("in-app" in question_lower or "ads" in question_lower):
            assumptions.append("• Revenue includes both in-app purchases and advertising")
        
        if assumptions:
            return "\n\n**Assumptions made:**\n" + "\n".join(assumptions)
        
        return ""
    
    def format_response(self, query_result: Dict[str, Any], question: str) -> Dict[str, Any]:
        """
        Format the complete response for a query.
        
        Args:
            query_result: Result from SQL engine
            question: Original user question
            
        Returns:
            Formatted response dictionary
        """
        results = query_result.get("result_data", [])
        query_type = query_result.get("query_type", "DETAILED_ANALYSIS")
        result_count = query_result.get("result_count", 0)
        sql_query = query_result.get("sql_query", "")
        from_cache = query_result.get("from_cache", False)
        
        # Determine response format
        use_simple_format = self._should_use_simple_format(query_type, result_count, question)
        
        # Generate main response
        if use_simple_format:
            main_response = self._create_simple_response(results, question, query_type)
            response_type = "simple"
        else:
            main_response = self._create_table_response(results, question, query_type)
            response_type = "table"
        
        # Add assumptions
        assumptions = self._add_assumptions(question, results)
        full_response = main_response + assumptions
        
        # Add cache indicator if from cache
        if from_cache:
            full_response += "\n\n*📎 Retrieved from cache*"
        
        return {
            "response_text": full_response,
            "response_type": response_type,
            "sql_query": sql_query,
            "result_count": result_count,
            "results": results,
            "can_export_csv": result_count > 0,
            "assumptions": assumptions.strip() if assumptions else None
        }
    
    def format_off_topic_response(self, question: str) -> str:
        """
        Format response for off-topic questions.
        
        Args:
            question: User's question
            
        Returns:
            Polite rejection message
        """
        return ("🤖 I'm specialized in analyzing our mobile app portfolio data. "
                "I can help you with questions about app installs, revenue, user acquisition costs, "
                "platform performance, and country-specific metrics.\n\n"
                "Try asking something like:\n"
                "• 'How many apps do we have?'\n"
                "• 'Which country generates the most revenue?'\n"
                "• 'Show me iOS app performance this month'")
    
    def format_error_response(self, error_message: str) -> str:
        """
        Format error response with helpful information.
        
        Args:
            error_message: Error message
            
        Returns:
            User-friendly error response
        """
        return (f"❌ I encountered an issue processing your request: {error_message}\n\n"
                "Please try rephrasing your question or ask something like:\n"
                "• 'List all apps sorted by popularity'\n"
                "• 'What's our total revenue this month?'\n"
                "• 'Compare iOS vs Android performance'")


# Global instance
response_formatter = ResponseFormatter() 
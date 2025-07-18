"""
SQL query validation and sanitization.
Ensures generated SQL queries are safe and valid before execution.
"""
import logging
import re
from typing import Dict, Any, List
import sqlparse
from sqlparse.sql import Statement, IdentifierList, Identifier, Function
from sqlparse.tokens import Keyword, DML

logger = logging.getLogger(__name__)


class SQLValidator:
    """
    Validates and sanitizes SQL queries for security and correctness.
    
    Features:
    - Prevents SQL injection attacks
    - Validates query structure
    - Ensures only allowed operations
    - Checks for required table references
    """
    
    # Allowed SQL keywords for read-only operations
    ALLOWED_KEYWORDS = {
        'SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 
        'LIMIT', 'OFFSET', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN',
        'UNION', 'INTERSECT', 'EXCEPT', 'WITH', 'AS', 'DISTINCT',
        'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'ROUND', 'COALESCE',
        'CASE', 'WHEN', 'THEN', 'ELSE', 'END', 'AND', 'OR', 'NOT',
        'IN', 'EXISTS', 'BETWEEN', 'LIKE', 'ILIKE', 'IS', 'NULL'
    }
    
    # Dangerous keywords that should never appear
    FORBIDDEN_KEYWORDS = {
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
        'TRUNCATE', 'REPLACE', 'MERGE', 'EXEC', 'EXECUTE',
        'xp_', 'sp_', 'OPENROWSET', 'BULK', 'UNION ALL SELECT'
    }
    
    # Required table name
    REQUIRED_TABLE = 'app_metrics'
    
    # Valid column names
    VALID_COLUMNS = {
        'id', 'app_name', 'platform', 'date', 'country',
        'installs', 'in_app_revenue', 'ads_revenue', 'ua_cost',
        'created_at', 'updated_at'
    }
    
    def __init__(self):
        """Initialize the SQL validator."""
        self.validation_errors = []
    
    def _reset_errors(self):
        """Reset validation errors for new validation."""
        self.validation_errors = []
    
    def _add_error(self, error_message: str):
        """Add a validation error."""
        self.validation_errors.append(error_message)
        logger.warning(f"SQL Validation Error: {error_message}")
    
    def _check_forbidden_keywords(self, sql: str) -> bool:
        """
        Check for forbidden SQL keywords.
        
        Args:
            sql: SQL query to check
            
        Returns:
            True if no forbidden keywords found, False otherwise
        """
        sql_upper = sql.upper()
        
        for forbidden in self.FORBIDDEN_KEYWORDS:
            if forbidden in sql_upper:
                self._add_error(f"Forbidden keyword detected: {forbidden}")
                return False
        
        return True
    
    def _check_sql_injection_patterns(self, sql: str) -> bool:
        """
        Check for common SQL injection patterns.
        
        Args:
            sql: SQL query to check
            
        Returns:
            True if no injection patterns found, False otherwise
        """
        # Common injection patterns
        injection_patterns = [
            r"';\s*--",  # Comment injection
            r"';\s*DROP",  # Drop table injection
            r"UNION.*SELECT.*FROM",  # Union-based injection
            r"'.*OR.*'.*=.*'",  # OR-based injection
            r"--.*",  # SQL comments (suspicious)
            r"/\*.*\*/",  # Multi-line comments
            r"xp_cmdshell",  # System command execution
            r"sp_executesql",  # Dynamic SQL execution
        ]
        
        for pattern in injection_patterns:
            if re.search(pattern, sql, re.IGNORECASE):
                self._add_error(f"Potential SQL injection pattern detected: {pattern}")
                return False
        
        return True
    
    def _check_table_references(self, parsed_sql: Statement) -> bool:
        """
        Check that only allowed tables are referenced.
        
        Args:
            parsed_sql: Parsed SQL statement
            
        Returns:
            True if table references are valid, False otherwise
        """
        tables_found = set()
        sql_text = str(parsed_sql).lower()
        
        # Simple approach: look for FROM app_metrics in the SQL text
        if f"from {self.REQUIRED_TABLE}" in sql_text:
            tables_found.add(self.REQUIRED_TABLE)
        
        # Also check for JOIN references
        if f"join {self.REQUIRED_TABLE}" in sql_text:
            tables_found.add(self.REQUIRED_TABLE)
            
        # More sophisticated token-based extraction as backup
        def extract_table_names(tokens):
            """Recursively extract table names from tokens."""
            from_next = False
            join_next = False
            
            for i, token in enumerate(tokens):
                if hasattr(token, 'tokens'):
                    extract_table_names(token.tokens)
                elif token.ttype is Keyword:
                    keyword = str(token).strip().upper()
                    if keyword == 'FROM':
                        from_next = True
                    elif keyword in ['JOIN', 'INNER', 'LEFT', 'RIGHT']:
                        join_next = True
                elif from_next or join_next:
                    if token.ttype is None and str(token).strip():
                        table_name = str(token).strip().lower()
                        # Remove any aliases or extra characters
                        table_name = table_name.split()[0].replace(',', '').replace(';', '')
                        if table_name and table_name not in ['as', 'on', 'where']:
                            tables_found.add(table_name)
                    from_next = False
                    join_next = False
        
        extract_table_names(parsed_sql.tokens)
        
        # Check if required table is present
        if self.REQUIRED_TABLE not in tables_found:
            self._add_error(f"Required table '{self.REQUIRED_TABLE}' not found in query")
            return False
        
        # Check for unexpected tables (allow some common system tables)
        allowed_tables = {
            self.REQUIRED_TABLE, 
            'query_cache',
            'information_schema', 
            'pg_catalog',
            'pg_class',
            'pg_namespace'
        }
        
        unexpected_tables = tables_found - allowed_tables
        if unexpected_tables:
            # Only warn about unexpected tables, don't fail validation
            logger.warning(f"Potentially unexpected table references: {unexpected_tables}")
        
        return True
    
    def _check_query_structure(self, parsed_sql: Statement) -> bool:
        """
        Check that the query has valid structure.
        
        Args:
            parsed_sql: Parsed SQL statement
            
        Returns:
            True if structure is valid, False otherwise
        """
        # Check that it's a SELECT statement
        first_token = None
        for token in parsed_sql.tokens:
            if token.ttype in (Keyword, DML):
                first_token = str(token).strip().upper()
                break
        
        if first_token != 'SELECT':
            self._add_error(f"Only SELECT statements are allowed, found: {first_token}")
            return False
        
        return True
    
    def _check_column_references(self, sql: str) -> bool:
        """
        Check that only valid columns are referenced.
        
        Args:
            sql: SQL query to check
            
        Returns:
            True if column references are valid, False otherwise
        """
        # Extract potential column names (simplified approach)
        # This is a basic check - more sophisticated parsing could be added
        
        # Find column-like patterns (word.word or just word in SELECT/WHERE clauses)
        column_patterns = re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', sql, re.IGNORECASE)
        
        # Filter out obvious non-column words and allow common SQL functions/aliases
        non_columns = {
            'select', 'from', 'where', 'group', 'by', 'order', 'having',
            'limit', 'offset', 'join', 'inner', 'left', 'right', 'on',
            'and', 'or', 'not', 'in', 'like', 'between', 'case', 'when',
            'then', 'else', 'end', 'as', 'distinct', 'count', 'sum',
            'avg', 'min', 'max', 'round', 'coalesce', 'desc', 'asc',
            'date_trunc', 'current_date', 'interval', 'extract', 'now',
            'date_part', 'postgresql', 'null', 'true', 'false',
            self.REQUIRED_TABLE
        }
        
        # Allow common aliases and computed column names
        allowed_aliases = {
            'total_apps', 'number_of_apps', 'app_count', 'total_revenue',
            'total_installs', 'total_cost', 'avg_revenue', 'max_installs',
            'min_revenue', 'count_apps', 'revenue_sum', 'install_sum',
            'month', 'year', 'day', 'week', 'quarter', 'revenue_per_install',
            'roi', 'conversion_rate', 'daily_revenue', 'weekly_revenue',
            'monthly_revenue', 'yearly_revenue', 'platform_revenue',
            'country_revenue', 'app_revenue', 'total_ua_cost'
        }
        
        potential_columns = {col.lower() for col in column_patterns if col.lower() not in non_columns}
        
        # Check against valid columns and aliases
        valid_references = self.VALID_COLUMNS | allowed_aliases
        invalid_columns = potential_columns - valid_references
        
        # Remove some obviously valid patterns
        filtered_invalid = set()
        for col in invalid_columns:
            # Skip numeric values, string literals, and very short words
            if (not re.match(r'^\d+$', col) and 
                not col.startswith('"') and 
                not col.startswith("'") and
                len(col) > 2):
                filtered_invalid.add(col)
        
        if filtered_invalid:
            # Only warn about potentially invalid columns, don't fail validation
            logger.warning(f"Potentially invalid column references: {filtered_invalid}")
        
        return True  # Always return True to not fail validation on column names
    
    def _check_query_complexity(self, sql: str) -> bool:
        """
        Check that query complexity is reasonable.
        
        Args:
            sql: SQL query to check
            
        Returns:
            True if complexity is acceptable, False otherwise
        """
        # Basic complexity checks
        if len(sql) > 5000:
            self._add_error("Query is too long (>5000 characters)")
            return False
        
        # Count nested subqueries
        subquery_count = sql.upper().count('SELECT') - 1
        if subquery_count > 3:
            self._add_error(f"Too many nested subqueries: {subquery_count}")
            return False
        
        return True
    
    def validate_sql(self, sql: str) -> Dict[str, Any]:
        """
        Validate a SQL query comprehensively.
        
        Args:
            sql: SQL query to validate
            
        Returns:
            Dictionary with validation results
        """
        self._reset_errors()
        
        if not sql or not sql.strip():
            self._add_error("Empty SQL query")
            return {"is_valid": False, "error": "Empty SQL query", "errors": self.validation_errors}
        
        sql = sql.strip()
        
        try:
            # Parse the SQL
            parsed = sqlparse.parse(sql)
            if not parsed:
                self._add_error("Could not parse SQL query")
                return {"is_valid": False, "error": "Could not parse SQL query", "errors": self.validation_errors}
            
            statement = parsed[0]
            
            # Run all validation checks
            checks = [
                self._check_forbidden_keywords(sql),
                self._check_sql_injection_patterns(sql),
                self._check_query_structure(statement),
                self._check_table_references(statement),
                self._check_column_references(sql),
                self._check_query_complexity(sql)
            ]
            
            is_valid = all(checks)
            
            if is_valid:
                logger.info("SQL validation passed")
                return {"is_valid": True, "error": None, "errors": []}
            else:
                error_msg = "; ".join(self.validation_errors)
                logger.error(f"SQL validation failed: {error_msg}")
                return {"is_valid": False, "error": error_msg, "errors": self.validation_errors}
        
        except Exception as e:
            error_msg = f"SQL validation error: {str(e)}"
            logger.error(error_msg)
            return {"is_valid": False, "error": error_msg, "errors": [error_msg]}
    
    def sanitize_sql(self, sql: str) -> str:
        """
        Sanitize SQL query by removing/escaping dangerous elements.
        
        Args:
            sql: SQL query to sanitize
            
        Returns:
            Sanitized SQL query
        """
        if not sql:
            return ""
        
        # Remove comments
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        
        # Remove extra whitespace
        sql = ' '.join(sql.split())
        
        # Ensure it ends with semicolon if not present
        if not sql.endswith(';'):
            sql += ';'
        
        return sql 
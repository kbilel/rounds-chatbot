"""
Test suite for the SQL generation engine.
Demonstrates testing structure and key test cases.
"""
import pytest
from unittest.mock import Mock, patch
import json

from ai.sql_engine import SQLGenerationEngine, sql_engine
from ai.query_validator import SQLValidator


class TestSQLGenerationEngine:
    """Test cases for the SQL generation engine."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create a mock SQL engine for testing."""
        with patch('ai.sql_engine.ChatOpenAI') as mock_llm:
            engine = SQLGenerationEngine()
            engine.llm = mock_llm
            return engine
    
    def test_classify_query_simple_count(self, mock_engine):
        """Test query classification for simple count questions."""
        with patch.object(mock_engine, 'llm') as mock_llm:
            mock_chain = Mock()
            mock_chain.invoke.return_value = "SIMPLE_COUNT"
            mock_llm.__or__ = Mock(return_value=mock_chain)
            
            result = mock_engine.classify_query("How many apps do we have?")
            assert result == "SIMPLE_COUNT"
    
    def test_classify_query_ranking(self, mock_engine):
        """Test query classification for ranking questions."""
        with patch.object(mock_engine, 'llm') as mock_llm:
            mock_chain = Mock()
            mock_chain.invoke.return_value = "RANKING"
            mock_llm.__or__ = Mock(return_value=mock_chain)
            
            result = mock_engine.classify_query("Show me top 10 apps by revenue")
            assert result == "RANKING"
    
    def test_generate_sql_success(self, mock_engine):
        """Test successful SQL generation."""
        with patch.object(mock_engine, 'llm') as mock_llm, \
             patch.object(mock_engine.validator, 'validate_sql') as mock_validator:
            
            # Mock successful SQL generation
            mock_chain = Mock()
            mock_chain.invoke.return_value = "SELECT COUNT(DISTINCT app_name) FROM app_metrics;"
            mock_llm.__or__ = Mock(return_value=mock_chain)
            
            # Mock successful validation
            mock_validator.return_value = {"is_valid": True, "error": None}
            
            result = mock_engine.generate_sql("How many apps do we have?")
            assert "SELECT COUNT(DISTINCT app_name)" in result
            assert "app_metrics" in result
    
    def test_generate_sql_validation_failure(self, mock_engine):
        """Test SQL generation with validation failure."""
        with patch.object(mock_engine, 'llm') as mock_llm, \
             patch.object(mock_engine.validator, 'validate_sql') as mock_validator:
            
            # Mock SQL generation
            mock_chain = Mock()
            mock_chain.invoke.return_value = "DROP TABLE app_metrics;"
            mock_llm.__or__ = Mock(return_value=mock_chain)
            
            # Mock validation failure
            mock_validator.return_value = {
                "is_valid": False, 
                "error": "Forbidden keyword detected: DROP"
            }
            
            with pytest.raises(ValueError, match="Generated SQL is invalid"):
                mock_engine.generate_sql("Delete all data")
    
    def test_is_app_analytics_question_valid(self, mock_engine):
        """Test detection of valid app analytics questions."""
        valid_questions = [
            "How many apps do we have?",
            "Show me Instagram revenue",
            "Which platform performs better?",
            "Total installs for iOS apps",
            "Revenue by country"
        ]
        
        for question in valid_questions:
            assert mock_engine.is_app_analytics_question(question) == True
    
    def test_is_app_analytics_question_invalid(self, mock_engine):
        """Test detection of invalid app analytics questions."""
        invalid_questions = [
            "What's the weather today?",
            "How are you doing?",
            "Tell me a joke",
            "What time is it?",
            "How to cook pasta?"
        ]
        
        for question in invalid_questions:
            assert mock_engine.is_app_analytics_question(question) == False
    
    @patch('ai.sql_engine.db_manager')
    def test_execute_sql_success(self, mock_db, mock_engine):
        """Test successful SQL execution."""
        # Mock database session and results
        mock_session = Mock()
        mock_result = Mock()
        mock_result.keys.return_value = ['count']
        mock_result.fetchall.return_value = [(5,)]
        mock_session.execute.return_value = mock_result
        
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        sql_query = "SELECT COUNT(DISTINCT app_name) FROM app_metrics;"
        results, count = mock_engine.execute_sql(sql_query)
        
        assert len(results) == 1
        assert results[0]['count'] == 5
        assert count == 1
    
    @patch('ai.sql_engine.db_manager')
    def test_execute_sql_failure(self, mock_db, mock_engine):
        """Test SQL execution failure."""
        # Mock database session that raises an exception
        mock_session = Mock()
        mock_session.execute.side_effect = Exception("Database error")
        mock_db.get_session.return_value.__enter__.return_value = mock_session
        
        with pytest.raises(Exception, match="Failed to execute query"):
            mock_engine.execute_sql("INVALID SQL")


class TestSQLValidator:
    """Test cases for the SQL validator."""
    
    @pytest.fixture
    def validator(self):
        """Create a SQL validator instance."""
        return SQLValidator()
    
    def test_validate_sql_valid_select(self, validator):
        """Test validation of valid SELECT query."""
        sql = "SELECT app_name, SUM(installs) FROM app_metrics GROUP BY app_name;"
        result = validator.validate_sql(sql)
        
        assert result["is_valid"] == True
        assert result["error"] is None
    
    def test_validate_sql_forbidden_drop(self, validator):
        """Test validation rejects DROP statements."""
        sql = "DROP TABLE app_metrics;"
        result = validator.validate_sql(sql)
        
        assert result["is_valid"] == False
        assert "Forbidden keyword detected: DROP" in result["error"]
    
    def test_validate_sql_forbidden_insert(self, validator):
        """Test validation rejects INSERT statements."""
        sql = "INSERT INTO app_metrics VALUES (1, 'test', 'iOS', '2024-01-01', 'USA', 100, 50, 25, 10);"
        result = validator.validate_sql(sql)
        
        assert result["is_valid"] == False
        assert "Forbidden keyword detected: INSERT" in result["error"]
    
    def test_validate_sql_injection_pattern(self, validator):
        """Test validation detects SQL injection patterns."""
        sql = "SELECT * FROM app_metrics WHERE app_name = 'test'; DROP TABLE app_metrics; --'"
        result = validator.validate_sql(sql)
        
        assert result["is_valid"] == False
        assert "injection" in result["error"].lower()
    
    def test_validate_sql_empty_query(self, validator):
        """Test validation of empty query."""
        result = validator.validate_sql("")
        
        assert result["is_valid"] == False
        assert result["error"] == "Empty SQL query"
    
    def test_validate_sql_non_select_statement(self, validator):
        """Test validation rejects non-SELECT statements."""
        sql = "UPDATE app_metrics SET installs = 1000 WHERE app_name = 'TikTok';"
        result = validator.validate_sql(sql)
        
        assert result["is_valid"] == False
        assert "Only SELECT statements are allowed" in result["error"]


class TestIntegration:
    """Integration tests for the SQL engine."""
    
    @patch('ai.sql_engine.db_manager')
    @patch('ai.sql_engine.QueryCache')
    def test_process_query_end_to_end(self, mock_cache, mock_db):
        """Test complete query processing pipeline."""
        # Mock successful processing
        with patch.object(sql_engine, 'classify_query') as mock_classify, \
             patch.object(sql_engine, 'generate_sql') as mock_generate, \
             patch.object(sql_engine, 'execute_sql') as mock_execute, \
             patch.object(sql_engine, '_check_cache') as mock_check_cache, \
             patch.object(sql_engine, '_save_to_cache') as mock_save_cache:
            
            # Mock cache miss
            mock_check_cache.return_value = None
            
            # Mock successful processing
            mock_classify.return_value = "SIMPLE_COUNT"
            mock_generate.return_value = "SELECT COUNT(DISTINCT app_name) FROM app_metrics;"
            mock_execute.return_value = ([{"count": 20}], 1)
            
            result = sql_engine.process_query("How many apps do we have?")
            
            assert result["sql_query"] == "SELECT COUNT(DISTINCT app_name) FROM app_metrics;"
            assert result["result_data"] == [{"count": 20}]
            assert result["result_count"] == 1
            assert result["query_type"] == "SIMPLE_COUNT"
            assert result["from_cache"] == False
            
            # Verify cache was called
            mock_save_cache.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__]) 
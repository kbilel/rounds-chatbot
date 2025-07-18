"""
User session management for the Slack bot.
Tracks user interactions and maintains context for follow-up requests.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import json
import redis

from config import settings

logger = logging.getLogger(__name__)

class UserSessionManager:
    """
    Manages user sessions and query history for context-aware interactions.
    
    Features:
    - Store recent query results for CSV export and SQL display
    - Track user preferences and patterns
    - Maintain conversation context
    - Automatic session cleanup
    """
    
    def __init__(self):
        """Initialize the user session manager."""
        self.redis_client = None
        self.in_memory_sessions = {}  # Fallback if Redis is not available
        self.session_ttl = 3600  # 1 hour session timeout
        self.max_query_history = settings.max_query_history
        
        try:
            self.redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info("Connected to Redis for session management")
        except Exception as e:
            logger.warning(f"Redis connection failed, using in-memory sessions: {e}")
            self.redis_client = None
    
    def _get_session_key(self, user_id: str) -> str:
        """Generate Redis key for user session."""
        return f"user_session:{user_id}"
    
    def _get_session_data(self, user_id: str) -> Dict[str, Any]:
        """
        Get session data for a user.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            User session data
        """
        if self.redis_client:
            try:
                session_key = self._get_session_key(user_id)
                session_data = self.redis_client.get(session_key)
                
                if session_data:
                    return json.loads(session_data)
                else:
                    return self._create_new_session()
                    
            except Exception as e:
                logger.error(f"Error getting session data from Redis: {e}")
                # Fall back to in-memory
                return self.in_memory_sessions.get(user_id, self._create_new_session())
        else:
            return self.in_memory_sessions.get(user_id, self._create_new_session())
    
    def _save_session_data(self, user_id: str, session_data: Dict[str, Any]):
        """
        Save session data for a user.
        
        Args:
            user_id: Slack user ID
            session_data: Session data to save
        """
        session_data["last_updated"] = datetime.now().isoformat()
        
        if self.redis_client:
            try:
                session_key = self._get_session_key(user_id)
                self.redis_client.setex(
                    session_key,
                    self.session_ttl,
                    json.dumps(session_data, default=str)
                )
            except Exception as e:
                logger.error(f"Error saving session data to Redis: {e}")
                # Fall back to in-memory
                self.in_memory_sessions[user_id] = session_data
        else:
            self.in_memory_sessions[user_id] = session_data
    
    def _create_new_session(self) -> Dict[str, Any]:
        """Create a new user session."""
        return {
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
            "query_history": [],
            "preferences": {
                "preferred_format": "auto",  # auto, simple, table
                "show_assumptions": True,
                "default_export_format": "csv"
            },
            "stats": {
                "total_queries": 0,
                "csv_exports": 0,
                "sql_requests": 0
            }
        }
    
    def store_query_result(self, user_id: str, question: str, query_result: Dict[str, Any]):
        """
        Store a query result in the user's session.
        
        Args:
            user_id: Slack user ID
            question: User's original question
            query_result: Query result from SQL engine
        """
        try:
            session_data = self._get_session_data(user_id)
            
            # Create query record
            query_record = {
                "timestamp": datetime.now().isoformat(),
                "question": question,
                "sql_query": query_result.get("sql_query", ""),
                "result_count": query_result.get("result_count", 0),
                "query_type": query_result.get("query_type", ""),
                "from_cache": query_result.get("from_cache", False),
                "result_data": query_result.get("result_data", [])
            }
            
            # Add to query history (keep only recent queries)
            session_data["query_history"].append(query_record)
            
            # Limit history size
            if len(session_data["query_history"]) > self.max_query_history:
                session_data["query_history"] = session_data["query_history"][-self.max_query_history:]
            
            # Update stats
            session_data["stats"]["total_queries"] += 1
            
            # Save session
            self._save_session_data(user_id, session_data)
            
            logger.info(f"Stored query result for user {user_id}: {question[:50]}...")
            
        except Exception as e:
            logger.error(f"Error storing query result: {e}", exc_info=True)
    
    def get_last_query_result(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the last query result for a user.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            Last query result or None if no history
        """
        try:
            session_data = self._get_session_data(user_id)
            query_history = session_data.get("query_history", [])
            
            if query_history:
                return query_history[-1]
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting last query result: {e}", exc_info=True)
            return None
    
    def get_query_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get recent query history for a user.
        
        Args:
            user_id: Slack user ID
            limit: Maximum number of queries to return
            
        Returns:
            List of recent query records
        """
        try:
            session_data = self._get_session_data(user_id)
            query_history = session_data.get("query_history", [])
            
            # Return most recent queries
            return query_history[-limit:] if query_history else []
            
        except Exception as e:
            logger.error(f"Error getting query history: {e}", exc_info=True)
            return []
    
    def update_preference(self, user_id: str, preference: str, value: Any):
        """
        Update a user preference.
        
        Args:
            user_id: Slack user ID
            preference: Preference name
            value: Preference value
        """
        try:
            session_data = self._get_session_data(user_id)
            
            if "preferences" not in session_data:
                session_data["preferences"] = {}
            
            session_data["preferences"][preference] = value
            self._save_session_data(user_id, session_data)
            
            logger.info(f"Updated preference for user {user_id}: {preference} = {value}")
            
        except Exception as e:
            logger.error(f"Error updating preference: {e}", exc_info=True)
    
    def get_preference(self, user_id: str, preference: str, default: Any = None) -> Any:
        """
        Get a user preference.
        
        Args:
            user_id: Slack user ID
            preference: Preference name
            default: Default value if preference not found
            
        Returns:
            Preference value or default
        """
        try:
            session_data = self._get_session_data(user_id)
            preferences = session_data.get("preferences", {})
            return preferences.get(preference, default)
            
        except Exception as e:
            logger.error(f"Error getting preference: {e}", exc_info=True)
            return default
    
    def increment_stat(self, user_id: str, stat_name: str):
        """
        Increment a user statistic.
        
        Args:
            user_id: Slack user ID
            stat_name: Name of the statistic to increment
        """
        try:
            session_data = self._get_session_data(user_id)
            
            if "stats" not in session_data:
                session_data["stats"] = {}
            
            current_value = session_data["stats"].get(stat_name, 0)
            session_data["stats"][stat_name] = current_value + 1
            
            self._save_session_data(user_id, session_data)
            
        except Exception as e:
            logger.error(f"Error incrementing stat: {e}", exc_info=True)
    
    def get_user_stats(self, user_id: str) -> Dict[str, int]:
        """
        Get user statistics.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            Dictionary of user statistics
        """
        try:
            session_data = self._get_session_data(user_id)
            return session_data.get("stats", {})
            
        except Exception as e:
            logger.error(f"Error getting user stats: {e}", exc_info=True)
            return {}
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions (for in-memory storage)."""
        if not self.redis_client and self.in_memory_sessions:
            cutoff_time = datetime.now() - timedelta(seconds=self.session_ttl)
            expired_users = []
            
            for user_id, session_data in self.in_memory_sessions.items():
                try:
                    last_updated = datetime.fromisoformat(session_data.get("last_updated", ""))
                    if last_updated < cutoff_time:
                        expired_users.append(user_id)
                except (ValueError, TypeError):
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                del self.in_memory_sessions[user_id]
            
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired sessions")
    
    def get_session_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get a summary of the user's session.
        
        Args:
            user_id: Slack user ID
            
        Returns:
            Session summary
        """
        try:
            session_data = self._get_session_data(user_id)
            query_history = session_data.get("query_history", [])
            stats = session_data.get("stats", {})
            
            return {
                "total_queries": len(query_history),
                "last_query_time": query_history[-1]["timestamp"] if query_history else None,
                "most_recent_question": query_history[-1]["question"] if query_history else None,
                "session_stats": stats,
                "session_age": session_data.get("created_at", "")
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary: {e}", exc_info=True)
            return {} 
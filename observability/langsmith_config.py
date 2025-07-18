"""
LangSmith observability configuration and setup.
Provides comprehensive tracing and monitoring for AI operations.
"""
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime
import json

from langsmith import Client
from langchain.callbacks.manager import get_openai_callback
from langchain.callbacks.tracers import LangChainTracer

from config import settings

logger = logging.getLogger(__name__)


class LangSmithManager:
    """
    Manages LangSmith observability and tracing.
    
    Features:
    - Automatic trace collection
    - Custom metrics tracking
    - Error monitoring
    - Performance analytics
    - Cost tracking
    """
    
    def __init__(self):
        """Initialize the LangSmith manager."""
        self.client = None
        self.tracer = None
        self.is_enabled = False
        
        self._setup_langsmith()
    
    def _setup_langsmith(self):
        """Set up LangSmith client and configuration."""
        try:
            if not settings.langchain_api_key:
                logger.warning("LangSmith API key not provided, observability disabled")
                return
            
            # Set environment variables for LangChain
            os.environ["LANGCHAIN_TRACING_V2"] = str(settings.langchain_tracing_v2).lower()
            os.environ["LANGCHAIN_ENDPOINT"] = settings.langchain_endpoint
            os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key
            os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
            
            # Initialize LangSmith client
            self.client = Client(
                api_url=settings.langchain_endpoint,
                api_key=settings.langchain_api_key
            )
            
            # Test connection
            try:
                self.client.read_project(project_name=settings.langchain_project)
                logger.info(f"Connected to LangSmith project: {settings.langchain_project}")
            except Exception:
                # Create project if it doesn't exist
                self.client.create_project(
                    project_name=settings.langchain_project,
                    description="Rounds Analytics Chatbot - AI observability and tracing"
                )
                logger.info(f"Created LangSmith project: {settings.langchain_project}")
            
            # Initialize tracer
            self.tracer = LangChainTracer(
                project_name=settings.langchain_project,
                client=self.client
            )
            
            self.is_enabled = True
            logger.info("LangSmith observability enabled")
            
        except Exception as e:
            logger.error(f"Failed to setup LangSmith: {e}")
            self.is_enabled = False
    
    def create_run(self, name: str, inputs: Dict[str, Any], 
                  run_type: str = "llm") -> Optional[str]:
        """
        Create a new run for tracking.
        
        Args:
            name: Name of the operation
            inputs: Input data for the operation
            run_type: Type of run (llm, chain, tool, etc.)
            
        Returns:
            Run ID if successful, None otherwise
        """
        if not self.is_enabled:
            return None
        
        try:
            run = self.client.create_run(
                name=name,
                inputs=inputs,
                run_type=run_type,
                project_name=settings.langchain_project,
                start_time=datetime.now()
            )
            return str(run.id) if run else None
            
        except Exception as e:
            logger.error(f"Failed to create LangSmith run: {e}")
            return None
    
    def update_run(self, run_id: str, outputs: Dict[str, Any], 
                   error: Optional[str] = None):
        """
        Update a run with outputs and completion status.
        
        Args:
            run_id: Run ID to update
            outputs: Output data from the operation
            error: Error message if operation failed
        """
        if not self.is_enabled or not run_id:
            return
        
        try:
            self.client.update_run(
                run_id=run_id,
                outputs=outputs,
                error=error,
                end_time=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Failed to update LangSmith run: {e}")
    
    def log_user_feedback(self, run_id: str, score: float, 
                         feedback: str = "", user_id: str = ""):
        """
        Log user feedback for a run.
        
        Args:
            run_id: Run ID to provide feedback for
            score: Feedback score (0.0 to 1.0)
            feedback: Text feedback
            user_id: User who provided feedback
        """
        if not self.is_enabled or not run_id:
            return
        
        try:
            self.client.create_feedback(
                run_id=run_id,
                key="user_rating",
                score=score,
                comment=feedback,
                correction=None
            )
            
            logger.info(f"Logged user feedback for run {run_id}: score={score}")
            
        except Exception as e:
            logger.error(f"Failed to log user feedback: {e}")
    
    def track_custom_metric(self, metric_name: str, value: float, 
                          metadata: Dict[str, Any] = None):
        """
        Track a custom metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            metadata: Additional metadata
        """
        if not self.is_enabled:
            return
        
        try:
            # Custom metrics tracking through runs
            run_id = self.create_run(
                name=f"metric_{metric_name}",
                inputs={"metric_name": metric_name, "metadata": metadata or {}},
                run_type="custom"
            )
            
            if run_id:
                self.update_run(
                    run_id=run_id,
                    outputs={"value": value, "timestamp": datetime.now().isoformat()}
                )
            
        except Exception as e:
            logger.error(f"Failed to track custom metric: {e}")
    
    def get_project_stats(self) -> Dict[str, Any]:
        """
        Get project statistics and metrics.
        
        Returns:
            Dictionary containing project statistics
        """
        if not self.is_enabled:
            return {}
        
        try:
            # Get recent runs
            runs = list(self.client.list_runs(
                project_name=settings.langchain_project,
                limit=100
            ))
            
            # Calculate basic statistics
            total_runs = len(runs)
            successful_runs = sum(1 for run in runs if not run.error)
            failed_runs = total_runs - successful_runs
            
            # Calculate average duration
            durations = []
            for run in runs:
                if run.start_time and run.end_time:
                    duration = (run.end_time - run.start_time).total_seconds()
                    durations.append(duration)
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "failed_runs": failed_runs,
                "success_rate": successful_runs / total_runs if total_runs > 0 else 0,
                "average_duration_seconds": avg_duration,
                "project_name": settings.langchain_project
            }
            
        except Exception as e:
            logger.error(f"Failed to get project stats: {e}")
            return {}


class PerformanceTracker:
    """
    Tracks performance metrics for cost optimization.
    
    Features:
    - Token usage tracking
    - Response time monitoring
    - Cache hit rate tracking
    - Error rate monitoring
    """
    
    def __init__(self):
        """Initialize the performance tracker."""
        self.metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0,
            "error_count": 0
        }
        self.langsmith = LangSmithManager()
    
    def track_query(self, question: str, response_time: float, 
                   from_cache: bool, token_usage: Dict[str, int] = None,
                   error: Optional[str] = None):
        """
        Track a query execution.
        
        Args:
            question: User question
            response_time: Response time in seconds
            from_cache: Whether result came from cache
            token_usage: Token usage information
            error: Error message if query failed
        """
        self.metrics["total_queries"] += 1
        
        if from_cache:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
        
        if error:
            self.metrics["error_count"] += 1
        
        # Update average response time
        current_avg = self.metrics["avg_response_time"]
        total_queries = self.metrics["total_queries"]
        self.metrics["avg_response_time"] = (
            (current_avg * (total_queries - 1) + response_time) / total_queries
        )
        
        # Track token usage if provided
        if token_usage:
            self.metrics["total_tokens"] += token_usage.get("total_tokens", 0)
            
            # Estimate cost (rough estimates for GPT-4)
            prompt_tokens = token_usage.get("prompt_tokens", 0)
            completion_tokens = token_usage.get("completion_tokens", 0)
            
            # GPT-4 pricing (approximate)
            prompt_cost = prompt_tokens * 0.00003  # $0.03 per 1K tokens
            completion_cost = completion_tokens * 0.00006  # $0.06 per 1K tokens
            total_cost = prompt_cost + completion_cost
            
            self.metrics["total_cost"] += total_cost
        
        # Send metrics to LangSmith
        self.langsmith.track_custom_metric("response_time", response_time, {
            "question_length": len(question),
            "from_cache": from_cache,
            "error": error
        })
        
        if token_usage:
            self.langsmith.track_custom_metric("token_usage", 
                                             token_usage.get("total_tokens", 0))
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of performance metrics.
        
        Returns:
            Dictionary containing performance metrics
        """
        cache_hit_rate = (
            self.metrics["cache_hits"] / self.metrics["total_queries"]
            if self.metrics["total_queries"] > 0 else 0
        )
        
        error_rate = (
            self.metrics["error_count"] / self.metrics["total_queries"]
            if self.metrics["total_queries"] > 0 else 0
        )
        
        return {
            **self.metrics,
            "cache_hit_rate": cache_hit_rate,
            "error_rate": error_rate,
            "avg_cost_per_query": (
                self.metrics["total_cost"] / self.metrics["total_queries"]
                if self.metrics["total_queries"] > 0 else 0
            )
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self.metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0,
            "error_count": 0
        }


# Global instances
langsmith_manager = LangSmithManager()
performance_tracker = PerformanceTracker() 
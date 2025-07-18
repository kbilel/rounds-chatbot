"""
Main application entry point for Rounds Analytics Slack Bot.
Initializes all components and starts the bot.
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from config import settings
from database import init_database, generate_sample_data
from slack_bot import analytics_bot
from observability.langsmith_config import langsmith_manager, performance_tracker

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('rounds_analytics_bot.log')
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown procedures.
    """
    # Startup
    logger.info("Starting Rounds Analytics Bot...")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        
        # Check if we need sample data
        from database import db_manager, AppMetrics
        with db_manager.get_session() as session:
            existing_data = session.query(AppMetrics).count()
            
            if existing_data == 0:
                logger.info("No existing data found, generating sample data...")
                try:
                    records_created = generate_sample_data(record_count=5000)
                    logger.info(f"Generated {records_created} sample records")
                except Exception as e:
                    logger.warning(f"Failed to generate sample data: {e}")
            else:
                logger.info(f"Found {existing_data} existing records in database")
        
        # Initialize LangSmith
        if langsmith_manager.is_enabled:
            logger.info("LangSmith observability initialized")
        else:
            logger.warning("LangSmith observability not available")
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Application startup failed: {e}")
        raise
    
    # Shutdown
    logger.info("Shutting down Rounds Analytics Bot...")
    
    # Cleanup any resources
    try:
        # Print final metrics
        metrics = performance_tracker.get_metrics_summary()
        logger.info(f"Final performance metrics: {metrics}")
        
        # Cleanup temp files
        from slack_bot.csv_handler import CSVHandler
        csv_handler = CSVHandler()
        csv_handler.cleanup_temp_files()
        
        logger.info("Application shutdown completed")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI app for health checks and metrics
app = FastAPI(
    title="Rounds Analytics Bot",
    description="AI-powered Slack chatbot for mobile app analytics",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        from database import db_manager
        db_healthy = db_manager.test_connection()
        
        # Check LangSmith status
        langsmith_status = "enabled" if langsmith_manager.is_enabled else "disabled"
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "langsmith": langsmith_status,
            "version": "1.0.0"
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "version": "1.0.0"
        }


@app.get("/metrics")
async def get_metrics():
    """Get application performance metrics."""
    try:
        performance_metrics = performance_tracker.get_metrics_summary()
        
        # Get LangSmith project stats if available
        langsmith_stats = {}
        if langsmith_manager.is_enabled:
            langsmith_stats = langsmith_manager.get_project_stats()
        
        # Get database stats
        from database import db_manager, AppMetrics
        with db_manager.get_session() as session:
            total_records = session.query(AppMetrics).count()
            
        return {
            "performance": performance_metrics,
            "langsmith": langsmith_stats,
            "database": {
                "total_records": total_records
            }
        }
        
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "name": "Rounds Analytics Bot",
        "description": "AI-powered Slack chatbot for mobile app analytics",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics"
        }
    }


async def start_slack_bot():
    """Start the Slack bot."""
    try:
        logger.info("Starting Slack bot...")
        await analytics_bot.start()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.error(f"Slack bot error: {e}")
        raise


async def main():
    """Main application function."""
    # Start both the web server and Slack bot
    try:
        # Create a server config
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8000,
            log_level=settings.log_level.lower()
        )
        server = uvicorn.Server(config)
        
        # Create tasks for both components
        web_task = asyncio.create_task(server.serve())
        slack_task = asyncio.create_task(start_slack_bot())
        
        logger.info("🚀 Starting Rounds Analytics Bot...")
        logger.info("📡 Web server will be available at http://localhost:8000")
        logger.info("🤖 Slack bot connecting...")
        
        # Wait for either task to complete (or fail)
        done, pending = await asyncio.wait(
            [web_task, slack_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            
        # Check if any task failed
        for task in done:
            if task.exception():
                raise task.exception()
                
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # Check if running in development mode
        if len(sys.argv) > 1:
            command = sys.argv[1]
            
            if command == "init-db":
                # Initialize database only
                logger.info("Initializing database...")
                init_database()
                logger.info("Database initialization completed")
                
            elif command == "generate-data":
                # Generate sample data
                logger.info("Generating sample data...")
                records_created = generate_sample_data(record_count=10000)
                logger.info(f"Generated {records_created} sample records")
                
            elif command == "reset-db":
                # Reset database with new sample data
                logger.info("Resetting database...")
                init_database()
                records_created = generate_sample_data(
                    complete_dataset=True,
                    apps_subset=["TikTok", "Instagram", "WhatsApp", "Facebook", "YouTube"]
                )
                logger.info(f"Database reset completed with {records_created} records")
                
            elif command == "start-bot":
                # Start only the Slack bot (no web server)
                logger.info("Starting Slack bot only...")
                asyncio.run(start_slack_bot())
                
            else:
                logger.error(f"Unknown command: {command}")
                logger.info("Available commands: init-db, generate-data, reset-db, start-bot")
                sys.exit(1)
        
        else:
            # Run the full application
            asyncio.run(main())
            
    except Exception as e:
        logger.error(f"Application failed to start: {e}")
        sys.exit(1) 
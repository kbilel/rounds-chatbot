"""
Database connection and session management.
"""
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

from config import settings
from .models import Base

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and operations.
    
    Provides connection pooling, session management, and database
    initialization functionality.
    """
    
    def __init__(self):
        """Initialize the database manager."""
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Create the SQLAlchemy engine with connection pooling."""
        try:
            self.engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=settings.debug,  # Log SQL queries in debug mode
            )
            
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            logger.info("Database engine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database engine: {e}")
            raise
    
    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    def drop_tables(self):
        """Drop all database tables (use with caution)."""
        try:
            Base.metadata.drop_all(bind=self.engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test the database connection."""
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                return result.scalar() == 1
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Provides automatic session cleanup and rollback on errors.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()


def get_db_session() -> Generator[Session, None, None]:
    """
    Dependency function for FastAPI to get database sessions.
    
    Yields:
        Database session that will be automatically closed.
    """
    with db_manager.get_session() as session:
        yield session


def init_database():
    """Initialize the database with tables."""
    logger.info("Initializing database...")
    
    # Test connection first
    if not db_manager.test_connection():
        raise ConnectionError("Cannot connect to database")
    
    # Create tables
    db_manager.create_tables()
    
    logger.info("Database initialization completed") 
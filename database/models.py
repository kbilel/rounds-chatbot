"""
Database models for the Rounds Analytics application.
Defines the schema for app portfolio analytics data.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Date, Numeric, DateTime, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates

Base = declarative_base()


class AppMetrics(Base):
    """
    Main table storing app portfolio analytics data.
    
    Contains daily metrics for mobile apps including installs,
    revenue, and user acquisition costs.
    """
    __tablename__ = "app_metrics"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Core Dimensions
    app_name = Column(String(100), nullable=False, index=True)
    platform = Column(String(10), nullable=False, index=True)
    date = Column(Date, nullable=False, index=True)
    country = Column(String(3), nullable=False, index=True)  # ISO 3-letter country codes
    
    # Metrics
    installs = Column(Integer, nullable=False, default=0)
    in_app_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)
    ads_revenue = Column(Numeric(12, 2), nullable=False, default=0.00)
    ua_cost = Column(Numeric(12, 2), nullable=False, default=0.00)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        # Unique constraint to prevent duplicate entries
        Index('idx_unique_app_metrics', 'app_name', 'platform', 'date', 'country', unique=True),
        
        # Performance indexes
        Index('idx_app_date', 'app_name', 'date'),
        Index('idx_platform_date', 'platform', 'date'),
        Index('idx_country_date', 'country', 'date'),
        Index('idx_date_only', 'date'),
        
        # Check constraints for data integrity
        CheckConstraint('installs >= 0', name='check_installs_non_negative'),
        CheckConstraint('in_app_revenue >= 0', name='check_in_app_revenue_non_negative'),
        CheckConstraint('ads_revenue >= 0', name='check_ads_revenue_non_negative'),
        CheckConstraint('ua_cost >= 0', name='check_ua_cost_non_negative'),
        CheckConstraint("platform IN ('iOS', 'Android')", name='check_valid_platform'),
    )
    
    @validates('platform')
    def validate_platform(self, key, platform):
        """Validate platform values."""
        if platform not in ['iOS', 'Android']:
            raise ValueError(f"Platform must be 'iOS' or 'Android', got: {platform}")
        return platform
    
    @validates('country')
    def validate_country(self, key, country):
        """Validate country code format."""
        if len(country) != 3:
            raise ValueError(f"Country must be a 3-letter ISO code, got: {country}")
        return country.upper()
    
    @property
    def total_revenue(self) -> Decimal:
        """Calculate total revenue from both in-app and ads."""
        return self.in_app_revenue + self.ads_revenue
    
    @property
    def roi(self) -> Optional[Decimal]:
        """Calculate Return on Investment (ROI) percentage."""
        if self.ua_cost > 0:
            return (self.total_revenue / self.ua_cost) * 100
        return None
    
    def __repr__(self):
        return (
            f"<AppMetrics(app='{self.app_name}', platform='{self.platform}', "
            f"date='{self.date}', country='{self.country}', installs={self.installs})>"
        )


class QueryCache(Base):
    """
    Cache table for storing query results to optimize token usage.
    
    Stores the SQL queries and their results to avoid regenerating
    the same data for repeated requests.
    """
    __tablename__ = "query_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_hash = Column(String(64), unique=True, nullable=False, index=True)
    natural_language_query = Column(String(1000), nullable=False)
    sql_query = Column(String(5000), nullable=False)
    result_data = Column(String, nullable=True)  # JSON string of results
    result_count = Column(Integer, nullable=False, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow, nullable=False)
    access_count = Column(Integer, default=1, nullable=False)
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_query_hash', 'query_hash'),
        Index('idx_created_at', 'created_at'),
        Index('idx_last_accessed', 'last_accessed'),
    )
    
    def __repr__(self):
        return (
            f"<QueryCache(hash='{self.query_hash[:8]}...', "
            f"count={self.result_count}, accessed={self.access_count})>"
        ) 
"""
Sample data generation for the Rounds Analytics application.
Creates realistic app portfolio analytics data for testing and demonstration.
"""
import logging
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any

from .connection import db_manager
from .models import AppMetrics

logger = logging.getLogger(__name__)


class SampleDataGenerator:
    """Generates realistic sample data for app analytics."""
    
    # Popular mobile apps for sample data
    APP_NAMES = [
        "TikTok", "Instagram", "WhatsApp", "Facebook", "YouTube",
        "Snapchat", "Twitter", "LinkedIn", "Pinterest", "Reddit",
        "Spotify", "Netflix", "Amazon", "Uber", "Airbnb",
        "Discord", "Twitch", "Duolingo", "Zoom", "PayPal"
    ]
    
    # Countries with their typical performance characteristics
    COUNTRIES = {
        "USA": {"install_multiplier": 1.5, "revenue_multiplier": 2.0},
        "GBR": {"install_multiplier": 1.2, "revenue_multiplier": 1.8},
        "DEU": {"install_multiplier": 1.1, "revenue_multiplier": 1.7},
        "FRA": {"install_multiplier": 1.0, "revenue_multiplier": 1.6},
        "JPN": {"install_multiplier": 0.8, "revenue_multiplier": 1.9},
        "KOR": {"install_multiplier": 0.9, "revenue_multiplier": 1.5},
        "CHN": {"install_multiplier": 2.0, "revenue_multiplier": 0.8},
        "IND": {"install_multiplier": 1.8, "revenue_multiplier": 0.6},
        "BRA": {"install_multiplier": 1.3, "revenue_multiplier": 0.9},
        "CAN": {"install_multiplier": 1.1, "revenue_multiplier": 1.7},
        "AUS": {"install_multiplier": 0.9, "revenue_multiplier": 1.6},
        "ESP": {"install_multiplier": 0.8, "revenue_multiplier": 1.3},
        "ITA": {"install_multiplier": 0.7, "revenue_multiplier": 1.2},
        "NLD": {"install_multiplier": 0.6, "revenue_multiplier": 1.8},
        "SWE": {"install_multiplier": 0.5, "revenue_multiplier": 1.9}
    }
    
    PLATFORMS = ["iOS", "Android"]
    
    def __init__(self, start_date: date = None, end_date: date = None):
        """
        Initialize the sample data generator.
        
        Args:
            start_date: Start date for data generation (default: 90 days ago)
            end_date: End date for data generation (default: today)
        """
        self.end_date = end_date or date.today()
        self.start_date = start_date or (self.end_date - timedelta(days=90))
        
        # Generate date range
        self.date_range = []
        current_date = self.start_date
        while current_date <= self.end_date:
            self.date_range.append(current_date)
            current_date += timedelta(days=1)
    
    def _generate_base_metrics(self, app_name: str, platform: str, 
                             country: str, target_date: date) -> Dict[str, Any]:
        """
        Generate base metrics for an app on a specific day.
        
        Uses realistic patterns and correlations between metrics.
        """
        country_data = self.COUNTRIES[country]
        
        # Base install range varies by app popularity
        popular_apps = ["TikTok", "Instagram", "WhatsApp", "Facebook", "YouTube"]
        if app_name in popular_apps:
            base_installs = random.randint(5000, 50000)
        else:
            base_installs = random.randint(500, 15000)
        
        # Apply country and platform multipliers
        installs = int(base_installs * country_data["install_multiplier"])
        
        # iOS typically has higher revenue per user
        if platform == "iOS":
            installs = int(installs * 0.7)  # Lower install volume
            revenue_multiplier = 1.5
        else:
            revenue_multiplier = 1.0
        
        # Weekend effect (higher usage on weekends)
        if target_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            installs = int(installs * 1.2)
            revenue_multiplier *= 1.3
        
        # Generate revenue metrics with realistic correlations
        # In-app revenue: $0.10 - $2.50 per install on average
        in_app_revenue_per_install = random.uniform(0.10, 2.50) * revenue_multiplier
        in_app_revenue = round(Decimal(str(installs * in_app_revenue_per_install)), 2)
        
        # Ads revenue: $0.05 - $0.80 per install on average
        ads_revenue_per_install = random.uniform(0.05, 0.80) * revenue_multiplier
        ads_revenue = round(Decimal(str(installs * ads_revenue_per_install)), 2)
        
        # UA cost: $0.20 - $5.00 per install (varies significantly)
        ua_cost_per_install = random.uniform(0.20, 5.00)
        ua_cost = round(Decimal(str(installs * ua_cost_per_install)), 2)
        
        return {
            "app_name": app_name,
            "platform": platform,
            "date": target_date,
            "country": country,
            "installs": installs,
            "in_app_revenue": in_app_revenue,
            "ads_revenue": ads_revenue,
            "ua_cost": ua_cost
        }
    
    def generate_metrics_batch(self, batch_size: int = 1000) -> List[AppMetrics]:
        """
        Generate a batch of app metrics records.
        
        Args:
            batch_size: Number of records to generate in this batch
            
        Returns:
            List of AppMetrics objects ready for database insertion
        """
        metrics_batch = []
        
        for _ in range(batch_size):
            # Randomly select dimensions
            app_name = random.choice(self.APP_NAMES)
            platform = random.choice(self.PLATFORMS)
            country = random.choice(list(self.COUNTRIES.keys()))
            target_date = random.choice(self.date_range)
            
            # Generate metrics
            metrics_data = self._generate_base_metrics(
                app_name, platform, country, target_date
            )
            
            # Create AppMetrics object
            metrics = AppMetrics(**metrics_data)
            metrics_batch.append(metrics)
        
        return metrics_batch
    
    def generate_complete_dataset(self, apps_subset: List[str] = None) -> int:
        """
        Generate a complete dataset with coverage across all dimensions.
        
        Args:
            apps_subset: List of specific apps to generate data for (default: all apps)
            
        Returns:
            Number of records created
        """
        apps_to_use = apps_subset or self.APP_NAMES
        total_records = 0
        
        logger.info(f"Generating complete dataset for {len(apps_to_use)} apps")
        logger.info(f"Date range: {self.start_date} to {self.end_date}")
        logger.info(f"Platforms: {self.PLATFORMS}")
        logger.info(f"Countries: {list(self.COUNTRIES.keys())}")
        
        with db_manager.get_session() as session:
            for app_name in apps_to_use:
                for platform in self.PLATFORMS:
                    for country in list(self.COUNTRIES.keys()):
                        for target_date in self.date_range:
                            # Generate metrics for this combination
                            metrics_data = self._generate_base_metrics(
                                app_name, platform, country, target_date
                            )
                            
                            # Create and add to session
                            metrics = AppMetrics(**metrics_data)
                            session.add(metrics)
                            total_records += 1
                            
                            # Commit in batches to avoid memory issues
                            if total_records % 1000 == 0:
                                session.commit()
                                logger.info(f"Committed {total_records} records")
            
            # Final commit
            session.commit()
        
        logger.info(f"Generated {total_records} total records")
        return total_records


def generate_sample_data(
    record_count: int = 10000,
    complete_dataset: bool = False,
    apps_subset: List[str] = None
) -> int:
    """
    Main function to generate sample data for the application.
    
    Args:
        record_count: Number of random records to generate (if not complete_dataset)
        complete_dataset: Whether to generate complete coverage dataset
        apps_subset: Specific apps to generate data for
        
    Returns:
        Number of records created
    """
    logger.info("Starting sample data generation...")
    
    # Check if data already exists
    with db_manager.get_session() as session:
        existing_count = session.query(AppMetrics).count()
        if existing_count > 0:
            logger.warning(f"Database already contains {existing_count} records")
            response = input("Do you want to clear existing data? (y/N): ")
            if response.lower() == 'y':
                session.query(AppMetrics).delete()
                session.commit()
                logger.info("Existing data cleared")
            else:
                logger.info("Keeping existing data, adding new records")
    
    # Generate data
    generator = SampleDataGenerator()
    
    if complete_dataset:
        return generator.generate_complete_dataset(apps_subset)
    else:
        # Generate random batch
        with db_manager.get_session() as session:
            batch_size = 1000
            total_created = 0
            
            while total_created < record_count:
                current_batch_size = min(batch_size, record_count - total_created)
                batch = generator.generate_metrics_batch(current_batch_size)
                
                session.bulk_save_objects(batch)
                session.commit()
                
                total_created += len(batch)
                logger.info(f"Generated {total_created}/{record_count} records")
            
            return total_created


if __name__ == "__main__":
    # Generate sample data when run directly
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "complete":
        records_created = generate_sample_data(complete_dataset=True)
    else:
        records_created = generate_sample_data(record_count=5000)
    
    print(f"Sample data generation completed: {records_created} records created") 
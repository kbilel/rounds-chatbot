"""
Configuration module for the Rounds Analytics Slack Bot.
Handles all environment variables and application settings.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Slack Configuration
    slack_bot_token: str = Field(..., env="SLACK_BOT_TOKEN")
    slack_signing_secret: str = Field(..., env="SLACK_SIGNING_SECRET")
    slack_app_token: str = Field(..., env="SLACK_APP_TOKEN")
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4-1106-preview", env="OPENAI_MODEL")
    
    # Database Configuration
    database_url: str = Field(..., env="DATABASE_URL")
    database_host: str = Field(default="localhost", env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="rounds_analytics", env="DATABASE_NAME")
    database_user: str = Field(..., env="DATABASE_USER")
    database_password: str = Field(..., env="DATABASE_PASSWORD")
    
    # LangSmith Configuration
    langchain_tracing_v2: bool = Field(default=True, env="LANGCHAIN_TRACING_V2")
    langchain_endpoint: str = Field(
        default="https://api.smith.langchain.com", 
        env="LANGCHAIN_ENDPOINT"
    )
    langchain_api_key: Optional[str] = Field(default=None, env="LANGCHAIN_API_KEY")
    langchain_project: str = Field(default="rounds-chatbot", env="LANGCHAIN_PROJECT")
    
    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    
    # Application Configuration
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    max_query_history: int = Field(default=10, env="MAX_QUERY_HISTORY")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()

# Example environment variables for documentation
ENV_EXAMPLE = """
# Slack Configuration
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_SIGNING_SECRET=your-signing-secret
SLACK_APP_TOKEN=xapp-your-app-token

# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-1106-preview

# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/rounds_analytics
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=rounds_analytics
DATABASE_USER=username
DATABASE_PASSWORD=password

# LangSmith Configuration
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_API_KEY=your-langsmith-api-key
LANGCHAIN_PROJECT=rounds-chatbot

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Application Configuration
DEBUG=true
LOG_LEVEL=INFO
MAX_QUERY_HISTORY=10
""" 
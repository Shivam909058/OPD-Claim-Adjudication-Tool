"""
Configuration settings for the OPD Claim Adjudication Tool.
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings."""
    
    # API Keys
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Database
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./opd_claims.db")
    
    # Server
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "7777"))
    debug: bool = os.getenv("DEBUG", "true").lower() == "true"
    
    # Model Configuration
    default_model: str = "gpt-4o-mini"  # Cost-effective and fast
    
    # Paths
    policy_terms_path: Path = BASE_DIR / "docs" / "policy_terms.json"
    adjudication_rules_path: Path = BASE_DIR / "docs" / "adjudication_rules.md"
    
    class Config:
        env_file = ".env"
        extra = "allow"


# Global settings instance
settings = Settings()

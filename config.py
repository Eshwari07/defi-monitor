"""
Configuration constants for the DeFi Protocol Monitor.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database
    DATABASE_URL: str = "sqlite:///./defi_monitor.db"
    
    # API Settings
    API_TIMEOUT_SECONDS: int = 10
    API_RETRY_ATTEMPTS: int = 3
    API_RETRY_DELAY_SECONDS: float = 1.0
    
    # DeFiLlama API
    DEFILLAMA_BASE_URL: str = "https://api.llama.fi"
    
    # Protocols to monitor
    PROTOCOLS: List[str] = ["felix", "hlp"]
    
    # Anomaly Detection Thresholds
    TVL_DROP_THRESHOLD: float = 0.20  # 20% drop triggers critical
    APY_MIN_THRESHOLD: float = 2.0    # Below 2% triggers warning
    UTILIZATION_MAX_THRESHOLD: float = 0.95  # Above 95% triggers warning
    
    # Lookback period for TVL comparison (in hours)
    TVL_LOOKBACK_HOURS: int = 24
    
    # Slack Integration (optional)
    SLACK_WEBHOOK_URL: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()

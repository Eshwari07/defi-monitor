"""
Pydantic schemas for API request/response models.
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
from decimal import Decimal


class ProtocolStatus(BaseModel):
    """Protocol health status response."""
    name: str
    tvl: Optional[float] = Field(None, description="TVL in USD")
    apy: Optional[float] = Field(None, description="7-day APY percentage")
    utilization: Optional[float] = Field(None, description="Utilization rate (0-1)")
    status: Literal["healthy", "warning", "critical"] = "healthy"
    
    class Config:
        from_attributes = True


class ProtocolHistory(BaseModel):
    """Historical data point."""
    timestamp: datetime
    tvl: Optional[float] = None
    apy: Optional[float] = None
    
    class Config:
        from_attributes = True


class AlertResponse(BaseModel):
    """Alert response model."""
    id: int
    protocol_name: str
    alert_type: str
    severity: Literal["critical", "warning", "info"]
    message: Optional[str] = None
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class HealthCheck(BaseModel):
    """API health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    protocols_monitored: int = 0
    active_alerts: int = 0

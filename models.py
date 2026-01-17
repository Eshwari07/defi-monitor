"""
SQLAlchemy models for protocol monitoring.
"""
from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, Text, UniqueConstraint
from sqlalchemy.sql import func
from database import Base


class ProtocolSnapshot(Base):
    """
    Stores periodic snapshots of protocol metrics.
    
    Attributes:
        protocol_name: Protocol identifier (e.g., 'felix', 'hlp')
        timestamp: When the snapshot was taken
        tvl_usd: Total Value Locked in USD
        apy_7d: 7-day average APY (percentage)
        utilization_rate: For lending protocols, utilization ratio (0-1)
    """
    __tablename__ = "protocol_snapshots"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    protocol_name = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    tvl_usd = Column(DECIMAL(20, 2), nullable=True)
    apy_7d = Column(DECIMAL(8, 4), nullable=True)
    utilization_rate = Column(DECIMAL(5, 4), nullable=True)  # For lending protocols
    
    # Ensure no duplicate entries for same protocol at same timestamp
    __table_args__ = (
        UniqueConstraint('protocol_name', 'timestamp', name='uq_protocol_timestamp'),
    )
    
    def __repr__(self):
        return f"<ProtocolSnapshot({self.protocol_name}, TVL=${self.tvl_usd}, APY={self.apy_7d}%)>"


class ProtocolAlert(Base):
    """
    Stores alerts triggered by anomaly detection.
    
    Attributes:
        protocol_name: Protocol that triggered the alert
        alert_type: Type of alert ('tvl_drop', 'apy_spike', 'utilization_high')
        severity: Alert severity ('critical', 'warning', 'info')
        message: Human-readable alert message
        triggered_at: When the alert was triggered
        resolved_at: When the alert was resolved (NULL if still active)
    """
    __tablename__ = "protocol_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    protocol_name = Column(String(50), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)  # 'tvl_drop', 'apy_spike', 'utilization_high'
    severity = Column(String(10), nullable=False)    # 'critical', 'warning', 'info'
    message = Column(Text, nullable=True)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<ProtocolAlert({self.protocol_name}, {self.alert_type}, {self.severity})>"

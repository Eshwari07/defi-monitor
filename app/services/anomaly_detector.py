"""
Anomaly detection for protocol metrics.

Implements alerting rules:
- TVL drop >20% in 24 hours → CRITICAL
- APY drops below 2% → WARNING  
- Utilization >95% for lending protocols → WARNING
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.models import ProtocolSnapshot, ProtocolAlert
from app.core.config import settings

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in protocol metrics and generates alerts."""
    
    # Lending protocols that have utilization rates
    LENDING_PROTOCOLS = {"felix"}
    
    def __init__(self):
        self.tvl_threshold = settings.TVL_DROP_THRESHOLD
        self.apy_min = settings.APY_MIN_THRESHOLD
        self.util_max = settings.UTILIZATION_MAX_THRESHOLD
        self.lookback_hours = settings.TVL_LOOKBACK_HOURS
    
    def detect_all(self) -> List[ProtocolAlert]:
        """
        Run all anomaly detection checks.
        
        Returns:
            List of generated alerts
        """
        db = SessionLocal()
        alerts: List[ProtocolAlert] = []
        
        try:
            protocols = self._get_active_protocols(db)
            
            for protocol in protocols:
                # Check TVL drop
                tvl_alert = self._check_tvl_drop(db, protocol)
                if tvl_alert:
                    alerts.append(tvl_alert)
                
                # Check APY threshold
                apy_alert = self._check_apy_low(db, protocol)
                if apy_alert:
                    alerts.append(apy_alert)
                
                # Check utilization (lending protocols only)
                if protocol in self.LENDING_PROTOCOLS:
                    util_alert = self._check_utilization_high(db, protocol)
                    if util_alert:
                        alerts.append(util_alert)
            
            return alerts
            
        finally:
            db.close()
    
    def _get_active_protocols(self, db) -> List[str]:
        """Get list of protocols with recent data."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
        
        results = db.query(ProtocolSnapshot.protocol_name).filter(
            ProtocolSnapshot.timestamp >= cutoff
        ).distinct().all()
        
        return [r[0] for r in results]
    
    def _check_tvl_drop(self, db, protocol: str) -> Optional[ProtocolAlert]:
        """
        Check for TVL drop >20% in 24 hours.
        
        Returns:
            ProtocolAlert if anomaly detected, None otherwise
        """
        now = datetime.now(timezone.utc)
        lookback = now - timedelta(hours=self.lookback_hours)
        
        # Get latest TVL
        latest = db.query(ProtocolSnapshot).filter(
            ProtocolSnapshot.protocol_name == protocol
        ).order_by(desc(ProtocolSnapshot.timestamp)).first()
        
        if not latest or not latest.tvl_usd:
            return None
        
        # Get TVL from 24 hours ago
        old = db.query(ProtocolSnapshot).filter(
            ProtocolSnapshot.protocol_name == protocol,
            ProtocolSnapshot.timestamp <= lookback
        ).order_by(desc(ProtocolSnapshot.timestamp)).first()
        
        if not old or not old.tvl_usd:
            return None
        
        # Calculate drop percentage
        current_tvl = float(latest.tvl_usd)
        old_tvl = float(old.tvl_usd)
        
        if old_tvl == 0:
            return None
        
        drop_pct = (old_tvl - current_tvl) / old_tvl
        
        if drop_pct > self.tvl_threshold:
            message = (
                f"TVL dropped {drop_pct:.1%} in {self.lookback_hours}h: "
                f"${old_tvl:,.0f} → ${current_tvl:,.0f}"
            )
            
            alert = self._create_alert(
                db=db,
                protocol_name=protocol,
                alert_type="tvl_drop",
                severity="critical",
                message=message
            )
            
            if alert:
                logger.critical(f"[{protocol}] {message}")
            
            return alert
        
        return None
    
    def _check_apy_low(self, db, protocol: str) -> Optional[ProtocolAlert]:
        """
        Check for APY below 2%.
        
        Returns:
            ProtocolAlert if anomaly detected, None otherwise
        """
        latest = db.query(ProtocolSnapshot).filter(
            ProtocolSnapshot.protocol_name == protocol
        ).order_by(desc(ProtocolSnapshot.timestamp)).first()
        
        if not latest or not latest.apy_7d:
            return None
        
        apy = float(latest.apy_7d)
        
        if apy < self.apy_min:
            message = f"APY at {apy:.2f}% (below {self.apy_min}% threshold)"
            
            alert = self._create_alert(
                db=db,
                protocol_name=protocol,
                alert_type="apy_low",
                severity="warning",
                message=message
            )
            
            if alert:
                logger.warning(f"[{protocol}] {message}")
            
            return alert
        
        return None
    
    def _check_utilization_high(self, db, protocol: str) -> Optional[ProtocolAlert]:
        """
        Check for utilization >95% (lending protocols only).
        
        Returns:
            ProtocolAlert if anomaly detected, None otherwise
        """
        latest = db.query(ProtocolSnapshot).filter(
            ProtocolSnapshot.protocol_name == protocol
        ).order_by(desc(ProtocolSnapshot.timestamp)).first()
        
        if not latest or not latest.utilization_rate:
            return None
        
        util = float(latest.utilization_rate)
        
        if util > self.util_max:
            message = f"Utilization at {util:.1%} (above {self.util_max:.0%} threshold)"
            
            alert = self._create_alert(
                db=db,
                protocol_name=protocol,
                alert_type="utilization_high",
                severity="warning",
                message=message
            )
            
            if alert:
                logger.warning(f"[{protocol}] {message}")
            
            return alert
        
        return None
    
    def _create_alert(
        self,
        db,
        protocol_name: str,
        alert_type: str,
        severity: str,
        message: str
    ) -> Optional[ProtocolAlert]:
        """
        Create an alert if one doesn't already exist for this issue.
        
        Avoids duplicate alerts by checking for unresolved alerts of same type.
        """
        # Check for existing unresolved alert
        existing = db.query(ProtocolAlert).filter(
            ProtocolAlert.protocol_name == protocol_name,
            ProtocolAlert.alert_type == alert_type,
            ProtocolAlert.resolved_at.is_(None)
        ).first()
        
        if existing:
            logger.debug(f"Alert already exists for {protocol_name}/{alert_type}")
            return None
        
        try:
            alert = ProtocolAlert(
                protocol_name=protocol_name,
                alert_type=alert_type,
                severity=severity,
                message=message,
                triggered_at=datetime.now(timezone.utc)
            )
            
            db.add(alert)
            db.commit()
            db.refresh(alert)
            
            logger.info(f"Created {severity} alert: {protocol_name}/{alert_type}")
            return alert
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating alert: {e}")
            return None

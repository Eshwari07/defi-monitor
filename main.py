"""
FastAPI application for DeFi Protocol Monitoring.

Provides health endpoints for:
- GET /protocols - List all protocols with status
- GET /protocols/{name}/history - Historical data
- GET /alerts - Active alerts  
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Literal
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from database import get_db, init_db
from models import ProtocolSnapshot, ProtocolAlert
from schemas import ProtocolStatus, ProtocolHistory, AlertResponse, HealthCheck
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DeFi Protocol Monitor",
    description="Monitors health metrics for DeFi protocols in vault allocation",
    version="1.0.0"
)

# Add CORS middleware for mobile app compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")


@app.get("/dashboard")
async def dashboard():
    """Serve the dashboard HTML page."""
    html_path = static_path / "index.html"
    if html_path.exists():
        return FileResponse(str(html_path))
    raise HTTPException(status_code=404, detail="Dashboard not found")


@app.get("/", response_model=HealthCheck)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    
    Returns API status and summary metrics.
    """
    protocols_count = db.query(
        func.count(func.distinct(ProtocolSnapshot.protocol_name))
    ).scalar() or 0
    
    active_alerts = db.query(func.count(ProtocolAlert.id)).filter(
        ProtocolAlert.resolved_at.is_(None)
    ).scalar() or 0
    
    return HealthCheck(
        status="ok",
        version="1.0.0",
        protocols_monitored=protocols_count,
        active_alerts=active_alerts
    )


@app.get("/protocols", response_model=List[ProtocolStatus])
async def get_protocols(db: Session = Depends(get_db)):
    """
    Get all protocols with their current status.
    
    Returns:
        List of protocols with name, tvl, apy, and health status
    """
    # Get distinct protocols
    protocols = db.query(
        func.distinct(ProtocolSnapshot.protocol_name)
    ).all()
    
    results = []
    
    for (protocol_name,) in protocols:
        # Get latest snapshot
        latest = db.query(ProtocolSnapshot).filter(
            ProtocolSnapshot.protocol_name == protocol_name
        ).order_by(desc(ProtocolSnapshot.timestamp)).first()
        
        if not latest:
            continue
        
        # Determine status based on active alerts
        status = _get_protocol_status(db, protocol_name)
        
        results.append(ProtocolStatus(
            name=protocol_name,
            tvl=float(latest.tvl_usd) if latest.tvl_usd else None,
            apy=float(latest.apy_7d) if latest.apy_7d else None,
            utilization=float(latest.utilization_rate) if latest.utilization_rate else None,
            status=status
        ))
    
    return results


@app.get("/protocols/{name}/history", response_model=List[ProtocolHistory])
async def get_protocol_history(
    name: str,
    days: int = Query(default=30, ge=1, le=365, description="Number of days of history"),
    db: Session = Depends(get_db)
):
    """
    Get historical data for a specific protocol.
    
    Args:
        name: Protocol name (e.g., 'felix', 'hlp')
        days: Number of days of history to return (default 30)
        
    Returns:
        List of historical data points with timestamp, tvl, and apy
    """
    # Check if protocol exists
    exists = db.query(ProtocolSnapshot).filter(
        ProtocolSnapshot.protocol_name == name
    ).first()
    
    if not exists:
        raise HTTPException(
            status_code=404,
            detail=f"Protocol '{name}' not found"
        )
    
    # Get historical data
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    
    snapshots = db.query(ProtocolSnapshot).filter(
        ProtocolSnapshot.protocol_name == name,
        ProtocolSnapshot.timestamp >= cutoff
    ).order_by(ProtocolSnapshot.timestamp).all()
    
    return [
        ProtocolHistory(
            timestamp=s.timestamp,
            tvl=float(s.tvl_usd) if s.tvl_usd else None,
            apy=float(s.apy_7d) if s.apy_7d else None
        )
        for s in snapshots
    ]


@app.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    status: Optional[Literal["open", "resolved", "all"]] = Query(
        default="open",
        description="Filter alerts by status"
    ),
    protocol: Optional[str] = Query(
        default=None,
        description="Filter by protocol name"
    ),
    severity: Optional[Literal["critical", "warning", "info"]] = Query(
        default=None,
        description="Filter by severity"
    ),
    db: Session = Depends(get_db)
):
    """
    Get alerts with optional filters.
    
    Args:
        status: Filter by alert status (open, resolved, all)
        protocol: Filter by protocol name
        severity: Filter by severity level
        
    Returns:
        List of alerts matching the filters
    """
    query = db.query(ProtocolAlert)
    
    # Filter by status
    if status == "open":
        query = query.filter(ProtocolAlert.resolved_at.is_(None))
    elif status == "resolved":
        query = query.filter(ProtocolAlert.resolved_at.isnot(None))
    
    # Filter by protocol
    if protocol:
        query = query.filter(ProtocolAlert.protocol_name == protocol)
    
    # Filter by severity
    if severity:
        query = query.filter(ProtocolAlert.severity == severity)
    
    # Order by most recent first
    alerts = query.order_by(desc(ProtocolAlert.triggered_at)).all()
    
    return [
        AlertResponse(
            id=a.id,
            protocol_name=a.protocol_name,
            alert_type=a.alert_type,
            severity=a.severity,
            message=a.message,
            triggered_at=a.triggered_at,
            resolved_at=a.resolved_at
        )
        for a in alerts
    ]


@app.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Mark an alert as resolved.
    
    Args:
        alert_id: ID of the alert to resolve
        
    Returns:
        Updated alert with resolved_at timestamp
    """
    alert = db.query(ProtocolAlert).filter(ProtocolAlert.id == alert_id).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    if alert.resolved_at:
        raise HTTPException(status_code=400, detail="Alert already resolved")
    
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    
    logger.info(f"Resolved alert {alert_id}: {alert.alert_type}")
    
    return AlertResponse(
        id=alert.id,
        protocol_name=alert.protocol_name,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        triggered_at=alert.triggered_at,
        resolved_at=alert.resolved_at
    )


def _get_protocol_status(db: Session, protocol_name: str) -> str:
    """
    Determine protocol status based on active alerts.
    
    Returns:
        'critical' if any critical alerts, 'warning' if warnings, else 'healthy'
    """
    # Check for critical alerts
    critical = db.query(ProtocolAlert).filter(
        ProtocolAlert.protocol_name == protocol_name,
        ProtocolAlert.severity == "critical",
        ProtocolAlert.resolved_at.is_(None)
    ).first()
    
    if critical:
        return "critical"
    
    # Check for warning alerts
    warning = db.query(ProtocolAlert).filter(
        ProtocolAlert.protocol_name == protocol_name,
        ProtocolAlert.severity == "warning",
        ProtocolAlert.resolved_at.is_(None)
    ).first()
    
    if warning:
        return "warning"
    
    return "healthy"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

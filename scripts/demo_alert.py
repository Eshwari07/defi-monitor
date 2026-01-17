import sys
import os
import logging
import asyncio
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from app.core.database import SessionLocal
from app.models.models import ProtocolSnapshot
from app.services.anomaly_detector import AnomalyDetector

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def insert_normal_data():
    """Insert 'normal' historical data for Felix (24 hours ago)."""
    db = SessionLocal()
    try:
        # Timestamp for 24 hours ago
        past_time = datetime.now(timezone.utc) - timedelta(hours=24, minutes=5)
        
        # Check if we already have data there
        existing = db.query(ProtocolSnapshot).filter(
            ProtocolSnapshot.protocol_name == "felix",
            ProtocolSnapshot.timestamp <= past_time
        ).first()

        if existing:
            logger.info("Found existing historical data, updating it to be 'High TVL'...")
            existing.tvl_usd = Decimal("100000000.00") # $100M similar to our mock base
            db.commit()
        else:
            logger.info("Inserting historical data (24h ago) with High TVL...")
            snapshot = ProtocolSnapshot(
                protocol_name="felix",
                timestamp=past_time,
                tvl_usd=Decimal("100000000.00"), # $100M
                apy_7d=Decimal("10.0"),
                utilization_rate=Decimal("0.80")
            )
            db.add(snapshot)
            db.commit()
            
    except Exception as e:
        logger.error(f"Error inserting normal data: {e}")
    finally:
        db.close()

def insert_crash_data():
    """Insert 'crash' data for Felix (NOW)."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        logger.info("Inserting CRASH data (NOW) with Low TVL (50% drop)...")
        
        # Simulate a 50% drop: $100M -> $50M
        # This is > 20% threshold, so it should trigger CRITICAL alert
        snapshot = ProtocolSnapshot(
            protocol_name="felix",
            timestamp=now,
            tvl_usd=Decimal("50000000.00"), # $50M
            apy_7d=Decimal("10.0"),
            utilization_rate=Decimal("0.80")
        )
        db.add(snapshot)
        db.commit()
        logger.info("Crash data inserted.")
            
    except Exception as e:
        logger.error(f"Error inserting crash data: {e}")
    finally:
        db.close()

async def run_detection():
    """Run the anomaly detector manually."""
    logger.info("Running anomaly detector...")
    detector = AnomalyDetector()
    alerts = detector.detect_all()
    
    if alerts:
        print("\n" + "="*50)
        print(f"SUCCESS! {len(alerts)} ALERTS DETECTED:")
        for alert in alerts:
            print(f"[{alert.severity.upper()}] {alert.protocol_name}: {alert.message}")
        print("="*50 + "\n")
    else:
        print("\nNo alerts detected. Check logic.\n")

if __name__ == "__main__":
    print("DEMO: Simulating a Protocol Crash")
    print("1. Ensuring high historical TVL exists...")
    insert_normal_data()
    
    print("2. Inserting recent 'crash' snapshot...")
    insert_crash_data()
    
    print("3. Running detection...")
    asyncio.run(run_detection())

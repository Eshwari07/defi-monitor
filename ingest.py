"""
Data ingestion script for protocol monitoring.

This script fetches metrics from all protocols and stores them
in the database. It is designed to be run periodically (e.g., via cron).

Features:
- Idempotent: Running twice for same timestamp doesn't duplicate data
- Resilient: Partial failures don't crash the pipeline
- Logged: All errors include context for debugging
"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Tuple, Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from database import init_db, SessionLocal
from models import ProtocolSnapshot
from fetchers.felix import FelixFetcher
from fetchers.hlp import HLPFetcher
from anomaly_detector import AnomalyDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DataIngestor:
    """Ingests protocol data into the database."""
    
    def __init__(self):
        self.felix_fetcher = FelixFetcher()
        self.hlp_fetcher = HLPFetcher()
        self.anomaly_detector = AnomalyDetector()
    
    async def ingest_all(self) -> Tuple[int, int]:
        """
        Ingest data for all protocols.
        
        Returns:
            Tuple of (successful_count, failed_count)
        """
        timestamp = datetime.now(timezone.utc)
        logger.info(f"Starting ingestion at {timestamp.isoformat()}")
        
        results: List[Tuple[str, bool, Any]] = []
        
        # Fetch all protocols concurrently
        # Even if one fails, others continue
        tasks = [
            self._ingest_felix(timestamp),
            self._ingest_hlp(timestamp),
        ]
        
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful = 0
        failed = 0
        
        for protocol, outcome in zip(["felix", "hlp"], outcomes):
            if isinstance(outcome, Exception):
                logger.error(f"Failed to ingest {protocol}: {outcome}")
                failed += 1
            elif outcome:
                successful += 1
            else:
                failed += 1
        
        logger.info(f"Ingestion complete: {successful} successful, {failed} failed")
        
        # Run anomaly detection after ingestion
        await self._run_anomaly_detection()
        
        return successful, failed
    
    async def _ingest_felix(self, timestamp: datetime) -> bool:
        """Ingest Felix protocol data."""
        try:
            metrics = await self.felix_fetcher.fetch_metrics()
            return self._store_snapshot(
                protocol_name="felix",
                timestamp=timestamp,
                tvl_usd=metrics.tvl_usd,
                apy_7d=metrics.apy_7d,
                utilization_rate=metrics.utilization_rate
            )
        except Exception as e:
            logger.error(f"Error fetching Felix metrics: {e}", exc_info=True)
            return False
    
    async def _ingest_hlp(self, timestamp: datetime) -> bool:
        """Ingest HLP vault data."""
        try:
            metrics = await self.hlp_fetcher.fetch_metrics()
            return self._store_snapshot(
                protocol_name="hlp",
                timestamp=timestamp,
                tvl_usd=metrics.tvl_usd,
                apy_7d=metrics.apy_7d,
                utilization_rate=metrics.utilization_rate
            )
        except Exception as e:
            logger.error(f"Error fetching HLP metrics: {e}", exc_info=True)
            return False
    
    def _store_snapshot(
        self,
        protocol_name: str,
        timestamp: datetime,
        tvl_usd: float | None,
        apy_7d: float | None,
        utilization_rate: float | None
    ) -> bool:
        """
        Store a protocol snapshot in the database.
        
        Uses INSERT ... ON CONFLICT DO NOTHING for idempotency.
        """
        db = SessionLocal()
        try:
            snapshot = ProtocolSnapshot(
                protocol_name=protocol_name,
                timestamp=timestamp,
                tvl_usd=Decimal(str(tvl_usd)) if tvl_usd else None,
                apy_7d=Decimal(str(apy_7d)) if apy_7d else None,
                utilization_rate=Decimal(str(utilization_rate)) if utilization_rate else None
            )
            
            db.add(snapshot)
            db.commit()
            
            logger.info(f"Stored snapshot for {protocol_name}: TVL=${tvl_usd:,.2f}")
            return True
            
        except IntegrityError:
            # Duplicate entry - this is expected for idempotency
            db.rollback()
            logger.info(f"Duplicate snapshot for {protocol_name} at {timestamp} - skipped")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error storing snapshot for {protocol_name}: {e}", exc_info=True)
            return False
            
        finally:
            db.close()
    
    async def _run_anomaly_detection(self):
        """Run anomaly detection on latest data."""
        try:
            alerts = self.anomaly_detector.detect_all()
            if alerts:
                logger.warning(f"Generated {len(alerts)} alerts")
            else:
                logger.info("No anomalies detected")
        except Exception as e:
            logger.error(f"Error running anomaly detection: {e}", exc_info=True)


async def main():
    """Main entry point for the ingestion script."""
    logger.info("Initializing database...")
    init_db()
    
    ingestor = DataIngestor()
    successful, failed = await ingestor.ingest_all()
    
    if failed > 0:
        logger.warning(f"Completed with {failed} failures")
        exit(1)
    else:
        logger.info("All protocols ingested successfully")
        exit(0)


if __name__ == "__main__":
    asyncio.run(main())

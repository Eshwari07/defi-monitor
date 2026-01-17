"""
Felix Protocol data fetcher.

Felix is a lending protocol on Hyperliquid L1 that offers:
- CDP markets (feUSD stablecoin)
- Vanilla lending pools with variable rates
- Stability pools for liquidation backstop

Since direct on-chain reads require complex Web3 setup,
we use DeFiLlama for TVL and mock realistic APY/utilization data.
"""
import logging
import random
from typing import Optional, Dict, Any
from dataclasses import dataclass
from fetchers.defillama import DeFiLlamaFetcher

logger = logging.getLogger(__name__)


@dataclass
class FelixMetrics:
    """Felix protocol metrics."""
    tvl_usd: Optional[float]
    apy_7d: Optional[float]
    utilization_rate: Optional[float]


class FelixFetcher:
    """Fetches Felix protocol metrics."""
    
    # Felix protocol slug on DeFiLlama
    DEFILLAMA_SLUG = "felix"
    
    # Realistic ranges for Felix lending pools
    APY_RANGE = (6.0, 14.0)  # 6-14% APY typical for lending
    UTILIZATION_RANGE = (0.65, 0.92)  # 65-92% utilization
    
    def __init__(self):
        self.defillama = DeFiLlamaFetcher()
    
    async def fetch_metrics(self) -> FelixMetrics:
        """
        Fetch all Felix protocol metrics.
        
        Returns:
            FelixMetrics with TVL, APY, and utilization
        """
        # Fetch TVL from DeFiLlama
        tvl = await self.defillama.fetch_tvl(self.DEFILLAMA_SLUG)
        
        if tvl is None:
            # If DeFiLlama fails, use a realistic mock value
            tvl = self._mock_tvl()
            logger.warning(f"Using mock TVL for Felix: ${tvl:,.2f}")
        
        # Generate realistic APY and utilization
        # In production, these would come from on-chain reads
        apy = self._mock_apy()
        utilization = self._mock_utilization()
        
        logger.info(
            f"Felix metrics: TVL=${tvl:,.2f}, APY={apy:.2f}%, "
            f"Utilization={utilization:.2%}"
        )
        
        return FelixMetrics(
            tvl_usd=tvl,
            apy_7d=apy,
            utilization_rate=utilization
        )
    
    def _mock_tvl(self) -> float:
        """Generate realistic mock TVL for Felix."""
        # Felix TVL typically in $50M-$200M range
        base_tvl = 85_000_000  # $85M base
        variance = random.uniform(-0.1, 0.1)  # ±10% variance
        return base_tvl * (1 + variance)
    
    def _mock_apy(self) -> float:
        """Generate realistic mock 7-day APY."""
        # Add some realistic variance
        return random.uniform(*self.APY_RANGE)
    
    def _mock_utilization(self) -> float:
        """Generate realistic mock utilization rate."""
        return random.uniform(*self.UTILIZATION_RANGE)

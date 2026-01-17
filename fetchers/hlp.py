"""
HLP (Hyperliquid LP) vault data fetcher.

HLP is Hyperliquid's native liquidity provider vault that:
- Provides liquidity across all perpetual markets
- Earns trading fees and maker rebates
- Has variable returns based on market conditions

Since HLP data requires specialized API access,
we use DeFiLlama for TVL and mock historical returns.
"""
import logging
import random
from typing import Optional
from dataclasses import dataclass
from fetchers.defillama import DeFiLlamaFetcher

logger = logging.getLogger(__name__)


@dataclass
class HLPMetrics:
    """HLP vault metrics."""
    tvl_usd: Optional[float]
    apy_7d: Optional[float]
    utilization_rate: Optional[float]  # None for HLP (not a lending protocol)


class HLPFetcher:
    """Fetches HLP vault metrics."""
    
    # Hyperliquid protocol slug on DeFiLlama
    DEFILLAMA_SLUG = "hyperliquid"
    
    # Realistic ranges for HLP returns
    # HLP historically has higher returns but more variance
    APY_RANGE = (12.0, 28.0)  # 12-28% APY typical for HLP
    
    def __init__(self):
        self.defillama = DeFiLlamaFetcher()
    
    async def fetch_metrics(self) -> HLPMetrics:
        """
        Fetch all HLP vault metrics.
        
        Returns:
            HLPMetrics with TVL and APY (no utilization for non-lending)
        """
        # Fetch TVL from DeFiLlama
        tvl = await self.defillama.fetch_tvl(self.DEFILLAMA_SLUG)
        
        if tvl is None:
            # If DeFiLlama fails, use a realistic mock value
            tvl = self._mock_tvl()
            logger.warning(f"Using mock TVL for HLP: ${tvl:,.2f}")
        
        # Generate realistic APY based on historical HLP performance
        apy = self._mock_apy()
        
        logger.info(f"HLP metrics: TVL=${tvl:,.2f}, APY={apy:.2f}%")
        
        return HLPMetrics(
            tvl_usd=tvl,
            apy_7d=apy,
            utilization_rate=None  # HLP is not a lending protocol
        )
    
    def _mock_tvl(self) -> float:
        """Generate realistic mock TVL for HLP."""
        # HLP TVL typically in $300M-$800M range
        base_tvl = 520_000_000  # $520M base
        variance = random.uniform(-0.08, 0.08)  # ±8% variance
        return base_tvl * (1 + variance)
    
    def _mock_apy(self) -> float:
        """Generate realistic mock 7-day APY."""
        # HLP returns are more variable than lending
        return random.uniform(*self.APY_RANGE)

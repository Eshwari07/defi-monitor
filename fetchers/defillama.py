"""
DeFiLlama API fetcher for TVL data.
"""
import httpx
import logging
from typing import Optional, Dict, Any
from config import settings

logger = logging.getLogger(__name__)


class DeFiLlamaFetcher:
    """Fetches protocol data from DeFiLlama API."""
    
    def __init__(self):
        self.base_url = settings.DEFILLAMA_BASE_URL
        self.timeout = settings.API_TIMEOUT_SECONDS
        self.max_retries = settings.API_RETRY_ATTEMPTS
        self.retry_delay = settings.API_RETRY_DELAY_SECONDS
    
    async def fetch_tvl(self, protocol: str) -> Optional[float]:
        """
        Fetch current TVL for a protocol.
        
        Args:
            protocol: Protocol slug (e.g., 'felix', 'hyperliquid')
            
        Returns:
            TVL in USD or None if fetch failed
        """
        url = f"{self.base_url}/tvl/{protocol}"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url)
                    
                    if response.status_code == 200:
                        # DeFiLlama returns just the TVL number for this endpoint
                        tvl = float(response.text)
                        logger.info(f"Successfully fetched TVL for {protocol}: ${tvl:,.2f}")
                        return tvl
                    
                    elif response.status_code >= 500:
                        logger.warning(
                            f"Server error {response.status_code} for {protocol}, "
                            f"attempt {attempt + 1}/{self.max_retries}"
                        )
                        if attempt < self.max_retries - 1:
                            import asyncio
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            continue
                    
                    elif response.status_code == 404:
                        logger.warning(f"Protocol {protocol} not found on DeFiLlama")
                        return None
                    
                    else:
                        logger.error(f"Unexpected status {response.status_code} for {protocol}")
                        return None
                        
            except httpx.TimeoutException:
                logger.warning(
                    f"Timeout fetching {protocol}, attempt {attempt + 1}/{self.max_retries}"
                )
                if attempt < self.max_retries - 1:
                    import asyncio
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                    
            except httpx.RequestError as e:
                logger.error(f"Request error for {protocol}: {e}")
                return None
                
            except ValueError as e:
                logger.error(f"Malformed response for {protocol}: {e}")
                return None
        
        logger.error(f"All retry attempts exhausted for {protocol}")
        return None
    
    async def fetch_protocol_data(self, protocol: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed protocol data including historical TVL.
        
        Args:
            protocol: Protocol slug
            
        Returns:
            Protocol data dict or None if fetch failed
        """
        url = f"{self.base_url}/protocol/{protocol}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Successfully fetched protocol data for {protocol}")
                    return data
                else:
                    logger.error(f"Failed to fetch protocol data: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching protocol data for {protocol}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing response: {e}")
            return None

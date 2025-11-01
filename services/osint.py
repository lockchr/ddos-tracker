"""
OSINT Integration Module
Provides integration with Shodan API for device intelligence and threat analysis.
"""

import logging
import time
from typing import Dict, List, Any, Optional
from functools import lru_cache
import requests

logger = logging.getLogger(__name__)


class ShodanClient:
    """Client for interacting with Shodan API"""
    
    def __init__(self, api_key: str, timeout: int = 10):
        """
        Initialize Shodan client.
        
        Args:
            api_key: Shodan API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self.base_url = "https://api.shodan.io"
        self._cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, float] = {}
        
    def _get_cache_key(self, endpoint: str, ip: str) -> str:
        """Generate cache key for requests"""
        return f"{endpoint}:{ip}"
    
    def _is_cache_valid(self, cache_key: str, cache_duration: int) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self._cache:
            return False
        
        timestamp = self._cache_timestamps.get(cache_key, 0)
        return (time.time() - timestamp) < cache_duration
    
    def _set_cache(self, cache_key: str, data: Any):
        """Store data in cache"""
        self._cache[cache_key] = data
        self._cache_timestamps[cache_key] = time.time()
    
    def get_ip_info(self, ip: str, cache_duration: int = 3600) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about an IP address from Shodan.
        
        Args:
            ip: IP address to look up
            cache_duration: Cache duration in seconds
            
        Returns:
            Dict containing IP information or None if request fails
        """
        cache_key = self._get_cache_key("host", ip)
        
        # Check cache first
        if self._is_cache_valid(cache_key, cache_duration):
            logger.debug(f"Returning cached Shodan data for {ip}")
            return self._cache[cache_key]
        
        try:
            url = f"{self.base_url}/shodan/host/{ip}"
            params = {"key": self.api_key}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse and structure the response
            result = {
                "ip": data.get("ip_str", ip),
                "organization": data.get("org", "Unknown"),
                "isp": data.get("isp", "Unknown"),
                "asn": data.get("asn", "Unknown"),
                "country": data.get("country_name", "Unknown"),
                "city": data.get("city", "Unknown"),
                "hostnames": data.get("hostnames", []),
                "domains": data.get("domains", []),
                "ports": data.get("ports", []),
                "vulns": data.get("vulns", []),
                "os": data.get("os", None),
                "tags": data.get("tags", []),
                "last_update": data.get("last_update", None),
                "services": []
            }
            
            # Extract service information
            for item in data.get("data", []):
                service = {
                    "port": item.get("port"),
                    "transport": item.get("transport", "tcp"),
                    "product": item.get("product", "Unknown"),
                    "version": item.get("version", ""),
                    "banner": item.get("data", "")[:200]  # Limit banner size
                }
                result["services"].append(service)
            
            # Cache the result
            self._set_cache(cache_key, result)
            logger.info(f"Retrieved Shodan data for {ip}")
            
            return result
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                logger.warning(f"IP {ip} not found in Shodan database")
            else:
                logger.error(f"Shodan API HTTP error for {ip}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Shodan API request failed for {ip}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error querying Shodan for {ip}: {e}")
            return None
    
    def search(self, query: str, max_results: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Search Shodan for devices matching a query.
        
        Args:
            query: Shodan search query
            max_results: Maximum number of results to return
            
        Returns:
            List of matching results or None if request fails
        """
        try:
            url = f"{self.base_url}/shodan/host/search"
            params = {
                "key": self.api_key,
                "query": query,
                "minify": True
            }
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            matches = data.get("matches", [])[:max_results]
            
            results = []
            for match in matches:
                result = {
                    "ip": match.get("ip_str"),
                    "port": match.get("port"),
                    "organization": match.get("org", "Unknown"),
                    "hostnames": match.get("hostnames", []),
                    "location": match.get("location", {}),
                    "banner": match.get("data", "")[:200]
                }
                results.append(result)
            
            logger.info(f"Shodan search returned {len(results)} results for query: {query}")
            return results
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Shodan search failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during Shodan search: {e}")
            return None
    
    def get_api_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the Shodan API key (credits, usage, etc).
        
        Returns:
            Dict containing API information or None if request fails
        """
        try:
            url = f"{self.base_url}/api-info"
            params = {"key": self.api_key}
            
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return {
                "query_credits": data.get("query_credits", 0),
                "scan_credits": data.get("scan_credits", 0),
                "plan": data.get("plan", "Unknown"),
                "usage_limits": data.get("usage_limits", {})
            }
            
        except Exception as e:
            logger.error(f"Failed to get Shodan API info: {e}")
            return None


class OSINTService:
    """Service for OSINT operations"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize OSINT service.
        
        Args:
            config: Configuration dictionary with OSINT settings
        """
        self.config = config
        self.shodan_client = None
        
        # Initialize Shodan if enabled and API key is provided
        shodan_config = config.get("osint", {}).get("shodan", {})
        if shodan_config.get("enabled") and shodan_config.get("api_key"):
            try:
                self.shodan_client = ShodanClient(
                    api_key=shodan_config["api_key"],
                    timeout=shodan_config.get("timeout", 10)
                )
                logger.info("Shodan client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Shodan client: {e}")
    
    def is_shodan_available(self) -> bool:
        """Check if Shodan integration is available"""
        return self.shodan_client is not None
    
    def enrich_ip_data(self, ip: str) -> Dict[str, Any]:
        """
        Enrich IP data with OSINT intelligence.
        
        Args:
            ip: IP address to enrich
            
        Returns:
            Dict containing enriched data
        """
        result = {
            "ip": ip,
            "shodan": None,
            "enriched": False
        }
        
        if self.shodan_client:
            shodan_config = self.config.get("osint", {}).get("shodan", {})
            cache_duration = shodan_config.get("cache_duration", 3600)
            
            shodan_data = self.shodan_client.get_ip_info(ip, cache_duration)
            if shodan_data:
                result["shodan"] = shodan_data
                result["enriched"] = True
        
        return result
    
    def search_threats(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for potential threats using Shodan.
        
        Args:
            query: Search query (e.g., "port:22 country:CN")
            
        Returns:
            List of potential threats or None
        """
        if not self.shodan_client:
            logger.warning("Shodan client not available for threat search")
            return None
        
        shodan_config = self.config.get("osint", {}).get("shodan", {})
        max_results = shodan_config.get("max_results", 10)
        
        return self.shodan_client.search(query, max_results)
    
    def get_shodan_api_status(self) -> Optional[Dict[str, Any]]:
        """
        Get Shodan API status and usage information.
        
        Returns:
            Dict containing API status or None
        """
        if not self.shodan_client:
            return None
        
        return self.shodan_client.get_api_info()

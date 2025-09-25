"""
Robots.txt Compliance and Politeness Utilities

This module provides utilities for robots.txt compliance checking and
politeness headers management for web scraping and API interactions.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse
import httpx
import json

logger = logging.getLogger(__name__)


@dataclass
class RobotsComplianceResult:
    """Result of robots.txt compliance check"""
    url: str
    is_allowed: bool
    user_agent: str
    robots_url: str
    crawl_delay: Optional[float] = None
    error_message: Optional[str] = None
    cache_timestamp: Optional[datetime] = None


@dataclass
class PolitenessHeaders:
    """Standard politeness headers for web requests"""
    user_agent: str
    accept: str
    accept_language: str
    accept_encoding: str
    connection: str
    cache_control: str
    additional_headers: Dict[str, str]


class RobotsComplianceManager:
    """
    Robots.txt Compliance Manager
    
    Manages robots.txt compliance checking, caching, and politeness
    headers for web scraping and API interactions.
    """
    
    def __init__(self, user_agent: str = "Provider-Validation-System/1.0"):
        """
        Initialize Robots Compliance Manager
        
        Args:
            user_agent: User agent string for requests
        """
        self.user_agent = user_agent
        self.robots_cache = {}
        self.crawl_delays = {}
        self.last_requests = {}
        
        # Standard politeness headers
        self.politeness_headers = PolitenessHeaders(
            user_agent=user_agent,
            accept="application/json, text/html, text/plain, */*",
            accept_language="en-US,en;q=0.9",
            accept_encoding="gzip, deflate, br",
            connection="keep-alive",
            cache_control="no-cache",
            additional_headers={
                "DNT": "1",  # Do Not Track
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Upgrade-Insecure-Requests": "1"
            }
        )
        
        # Rate limiting configuration
        self.default_delays = {
            "npi_registry": 0.1,  # 10 requests per second
            "google_places": 0.1,  # 10 requests per second
            "google_document_ai": 0.1,  # 10 requests per second
            "hospital_website": 2.0,  # 30 requests per minute
            "state_board": 2.0,  # 30 requests per minute
            "general": 1.0  # 1 request per second
        }
    
    async def check_robots_compliance(self, url: str, force_refresh: bool = False) -> RobotsComplianceResult:
        """
        Check robots.txt compliance for a URL
        
        Args:
            url: URL to check compliance for
            force_refresh: Force refresh of cached robots.txt
            
        Returns:
            RobotsComplianceResult with compliance information
        """
        try:
            # Parse URL to get base URL
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Check cache first
            if not force_refresh and base_url in self.robots_cache:
                cached_result = self.robots_cache[base_url]
                # Check if cache is still valid (24 hours)
                if cached_result.cache_timestamp:
                    age = datetime.now() - cached_result.cache_timestamp
                    if age.total_seconds() < 86400:  # 24 hours
                        logger.debug(f"Using cached robots.txt for {base_url}")
                        return cached_result
            
            # Fetch and parse robots.txt
            robots_url = urljoin(base_url, "/robots.txt")
            
            try:
                # Create robots.txt parser
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                # Read robots.txt
                rp.read()
                
                # Check if our user agent is allowed
                is_allowed = rp.can_fetch(self.user_agent, url)
                
                # Get crawl delay
                crawl_delay = rp.crawl_delay(self.user_agent)
                
                # Create result
                result = RobotsComplianceResult(
                    url=url,
                    is_allowed=is_allowed,
                    user_agent=self.user_agent,
                    robots_url=robots_url,
                    crawl_delay=crawl_delay,
                    cache_timestamp=datetime.now()
                )
                
                # Cache result
                self.robots_cache[base_url] = result
                
                logger.info(f"Robots.txt compliance check for {url}: {'ALLOWED' if is_allowed else 'BLOCKED'}")
                
                return result
            
            except Exception as e:
                logger.warning(f"Could not read robots.txt for {base_url}: {e}")
                
                # Default to allowing if robots.txt cannot be read
                result = RobotsComplianceResult(
                    url=url,
                    is_allowed=True,  # Default to allowing
                    user_agent=self.user_agent,
                    robots_url=robots_url,
                    error_message=str(e),
                    cache_timestamp=datetime.now()
                )
                
                self.robots_cache[base_url] = result
                return result
        
        except Exception as e:
            logger.error(f"Robots.txt compliance check failed for {url}: {e}")
            
            return RobotsComplianceResult(
                url=url,
                is_allowed=True,  # Default to allowing on error
                user_agent=self.user_agent,
                robots_url="",
                error_message=str(e),
                cache_timestamp=datetime.now()
            )
    
    def get_politeness_headers(self, additional_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Get standard politeness headers for requests
        
        Args:
            additional_headers: Additional headers to include
            
        Returns:
            Dictionary of headers for HTTP requests
        """
        headers = {
            "User-Agent": self.politeness_headers.user_agent,
            "Accept": self.politeness_headers.accept,
            "Accept-Language": self.politeness_headers.accept_language,
            "Accept-Encoding": self.politeness_headers.accept_encoding,
            "Connection": self.politeness_headers.connection,
            "Cache-Control": self.politeness_headers.cache_control
        }
        
        # Add additional headers
        headers.update(self.politeness_headers.additional_headers)
        
        # Add custom headers if provided
        if additional_headers:
            headers.update(additional_headers)
        
        return headers
    
    async def apply_rate_limiting(self, source: str, custom_delay: Optional[float] = None):
        """
        Apply rate limiting based on source and robots.txt crawl delay
        
        Args:
            source: Source identifier for rate limiting
            custom_delay: Custom delay to apply (overrides default)
        """
        try:
            # Determine delay
            if custom_delay is not None:
                delay = custom_delay
            elif source in self.default_delays:
                delay = self.default_delays[source]
            else:
                delay = self.default_delays["general"]
            
            # Check for robots.txt crawl delay
            if source in self.robots_cache:
                robots_result = self.robots_cache[source]
                if robots_result.crawl_delay:
                    # Use the maximum of our delay and robots.txt crawl delay
                    delay = max(delay, robots_result.crawl_delay)
            
            # Apply delay if needed
            if source in self.last_requests:
                time_since_last = time.time() - self.last_requests[source]
                if time_since_last < delay:
                    sleep_time = delay - time_since_last
                    logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
            
            # Update last request time
            self.last_requests[source] = time.time()
        
        except Exception as e:
            logger.error(f"Rate limiting error for {source}: {e}")
    
    async def make_polite_request(self, 
                                url: str, 
                                method: str = "GET",
                                headers: Optional[Dict[str, str]] = None,
                                data: Optional[Any] = None,
                                source: str = "general",
                                timeout: float = 30.0) -> httpx.Response:
        """
        Make a polite HTTP request with robots.txt compliance and rate limiting
        
        Args:
            url: URL to request
            method: HTTP method
            headers: Additional headers
            data: Request data
            source: Source identifier for rate limiting
            timeout: Request timeout
            
        Returns:
            httpx.Response object
            
        Raises:
            httpx.RequestError: If request fails
            ValueError: If robots.txt blocks the request
        """
        try:
            # Check robots.txt compliance
            compliance_result = await self.check_robots_compliance(url)
            
            if not compliance_result.is_allowed:
                raise ValueError(f"Robots.txt blocks access to {url} for user agent {self.user_agent}")
            
            # Apply rate limiting
            await self.apply_rate_limiting(source)
            
            # Prepare headers
            request_headers = self.get_politeness_headers(headers)
            
            # Make request
            async with httpx.AsyncClient(timeout=timeout) as client:
                if method.upper() == "GET":
                    response = await client.get(url, headers=request_headers)
                elif method.upper() == "POST":
                    response = await client.post(url, headers=request_headers, data=data)
                elif method.upper() == "PUT":
                    response = await client.put(url, headers=request_headers, data=data)
                elif method.upper() == "DELETE":
                    response = await client.delete(url, headers=request_headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Log request
                logger.info(f"Made polite {method} request to {url} (status: {response.status_code})")
                
                return response
        
        except httpx.RequestError as e:
            logger.error(f"HTTP request failed for {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Polite request failed for {url}: {e}")
            raise
    
    def get_crawl_delay(self, url: str) -> Optional[float]:
        """
        Get crawl delay for a URL from robots.txt
        
        Args:
            url: URL to get crawl delay for
            
        Returns:
            Crawl delay in seconds, or None if not specified
        """
        try:
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            if base_url in self.robots_cache:
                return self.robots_cache[base_url].crawl_delay
            
            return None
        
        except Exception as e:
            logger.error(f"Error getting crawl delay for {url}: {e}")
            return None
    
    def clear_cache(self):
        """Clear robots.txt cache"""
        self.robots_cache.clear()
        self.last_requests.clear()
        logger.info("Robots.txt cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            "cached_domains": len(self.robots_cache),
            "cached_urls": list(self.robots_cache.keys()),
            "last_requests": len(self.last_requests),
            "cache_timestamp": datetime.now().isoformat()
        }
    
    def update_user_agent(self, new_user_agent: str):
        """
        Update user agent string
        
        Args:
            new_user_agent: New user agent string
        """
        self.user_agent = new_user_agent
        self.politeness_headers.user_agent = new_user_agent
        # Clear cache since user agent changed
        self.clear_cache()
        logger.info(f"User agent updated to: {new_user_agent}")
    
    def add_custom_delay(self, source: str, delay: float):
        """
        Add custom delay for a specific source
        
        Args:
            source: Source identifier
            delay: Delay in seconds
        """
        self.default_delays[source] = delay
        logger.info(f"Added custom delay for {source}: {delay}s")
    
    def get_rate_limiting_info(self, source: str) -> Dict[str, Any]:
        """
        Get rate limiting information for a source
        
        Args:
            source: Source identifier
            
        Returns:
            Dictionary with rate limiting information
        """
        delay = self.default_delays.get(source, self.default_delays["general"])
        last_request = self.last_requests.get(source)
        
        info = {
            "source": source,
            "delay": delay,
            "requests_per_second": 1.0 / delay if delay > 0 else float('inf'),
            "last_request": last_request.isoformat() if last_request else None
        }
        
        # Add robots.txt crawl delay if available
        if source in self.robots_cache:
            robots_delay = self.robots_cache[source].crawl_delay
            if robots_delay:
                info["robots_crawl_delay"] = robots_delay
                info["effective_delay"] = max(delay, robots_delay)
        
        return info


# Global robots compliance manager instance
robots_manager = RobotsComplianceManager()


# Convenience functions
async def check_robots_compliance(url: str, user_agent: str = "Provider-Validation-System/1.0") -> RobotsComplianceResult:
    """
    Convenience function to check robots.txt compliance
    
    Args:
        url: URL to check
        user_agent: User agent string
        
    Returns:
        RobotsComplianceResult
    """
    manager = RobotsComplianceManager(user_agent)
    return await manager.check_robots_compliance(url)


def get_politeness_headers(user_agent: str = "Provider-Validation-System/1.0") -> Dict[str, str]:
    """
    Convenience function to get politeness headers
    
    Args:
        user_agent: User agent string
        
    Returns:
        Dictionary of headers
    """
    manager = RobotsComplianceManager(user_agent)
    return manager.get_politeness_headers()


async def make_polite_request(url: str, 
                            method: str = "GET",
                            headers: Optional[Dict[str, str]] = None,
                            data: Optional[Any] = None,
                            source: str = "general",
                            user_agent: str = "Provider-Validation-System/1.0") -> httpx.Response:
    """
    Convenience function to make a polite request
    
    Args:
        url: URL to request
        method: HTTP method
        headers: Additional headers
        data: Request data
        source: Source identifier
        user_agent: User agent string
        
    Returns:
        httpx.Response
    """
    manager = RobotsComplianceManager(user_agent)
    return await manager.make_polite_request(url, method, headers, data, source)


# Example usage and testing functions
async def example_robots_compliance():
    """
    Example function demonstrating robots.txt compliance
    """
    print("=" * 60)
    print("🤖 ROBOTS.TXT COMPLIANCE EXAMPLE")
    print("=" * 60)
    
    # Initialize robots compliance manager
    manager = RobotsComplianceManager()
    
    # Example URLs to check
    test_urls = [
        "https://npiregistry.cms.hhs.gov/api/",
        "https://maps.googleapis.com/maps/api/geocode/json",
        "https://www.example-hospital.com/provider-directory",
        "https://www.example-medical-board.com/license-lookup"
    ]
    
    print("\n📋 Checking robots.txt compliance:")
    
    for url in test_urls:
        print(f"\n🔍 Checking: {url}")
        
        try:
            result = await manager.check_robots_compliance(url)
            
            print(f"   Status: {'✅ ALLOWED' if result.is_allowed else '❌ BLOCKED'}")
            print(f"   User Agent: {result.user_agent}")
            print(f"   Robots URL: {result.robots_url}")
            
            if result.crawl_delay:
                print(f"   Crawl Delay: {result.crawl_delay}s")
            
            if result.error_message:
                print(f"   Error: {result.error_message}")
        
        except Exception as e:
            print(f"   Error: {e}")
    
    # Test politeness headers
    print(f"\n📋 Politeness Headers:")
    headers = manager.get_politeness_headers()
    for key, value in headers.items():
        print(f"   {key}: {value}")
    
    # Test rate limiting
    print(f"\n📋 Rate Limiting Information:")
    for source in ["npi_registry", "google_places", "hospital_website", "state_board"]:
        info = manager.get_rate_limiting_info(source)
        print(f"   {source}:")
        print(f"      Delay: {info['delay']}s")
        print(f"      Requests/sec: {info['requests_per_second']:.1f}")


def show_robots_compliance_best_practices():
    """
    Show robots.txt compliance best practices
    """
    print("\n" + "=" * 60)
    print("📋 ROBOTS.TXT COMPLIANCE BEST PRACTICES")
    print("=" * 60)
    
    print("✅ DO:")
    print("   • Always check robots.txt before scraping")
    print("   • Use descriptive user agent strings")
    print("   • Respect crawl delays")
    print("   • Cache robots.txt results")
    print("   • Implement rate limiting")
    print("   • Handle robots.txt errors gracefully")
    print("   • Use polite headers")
    print("   • Monitor for robots.txt changes")
    
    print("\n❌ DON'T:")
    print("   • Ignore robots.txt directives")
    print("   • Use generic or misleading user agents")
    print("   • Exceed crawl delays")
    print("   • Make requests too frequently")
    print("   • Scrape without permission")
    print("   • Ignore rate limiting")
    print("   • Use aggressive scraping patterns")
    
    print("\n📋 Recommended User Agent Format:")
    print("   Provider-Validation-System/1.0 (https://your-domain.com/contact)")
    
    print("\n📋 Standard Politeness Headers:")
    print("   • User-Agent: Descriptive and contactable")
    print("   • Accept: Appropriate content types")
    print("   • Accept-Language: Language preferences")
    print("   • Connection: keep-alive")
    print("   • DNT: 1 (Do Not Track)")


if __name__ == "__main__":
    # Run examples
    print("Robots.txt Compliance - Examples")
    print("To run examples:")
    print("1. Install dependencies: pip install httpx")
    print("2. Run: python -c 'from connectors.robots_compliance import example_robots_compliance; asyncio.run(example_robots_compliance())'")

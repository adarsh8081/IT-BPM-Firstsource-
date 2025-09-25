"""
Rate Limiter and Retry Policy

This module implements rate limiting per connector and retry policies for
the validation system with exponential backoff and circuit breaker patterns.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import redis
import json

logger = logging.getLogger(__name__)


class RateLimitType(Enum):
    """Rate limit types"""
    REQUESTS_PER_SECOND = "requests_per_second"
    REQUESTS_PER_MINUTE = "requests_per_minute"
    REQUESTS_PER_HOUR = "requests_per_hour"
    BURST_LIMIT = "burst_limit"


class RetryPolicy(Enum):
    """Retry policy types"""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    NO_RETRY = "no_retry"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    connector_name: str
    requests_per_second: float = 1.0
    requests_per_minute: int = 60
    requests_per_hour: int = 3600
    burst_limit: int = 10
    window_size: int = 60  # seconds


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    retry_on_errors: List[str] = None
    
    def __post_init__(self):
        if self.retry_on_errors is None:
            self.retry_on_errors = [
                "ConnectionError",
                "TimeoutError",
                "HTTPError",
                "ValidationError",
                "RateLimitError"
            ]


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3


class RateLimiter:
    """
    Rate Limiter with Redis-based sliding window
    
    Implements rate limiting per connector with configurable limits and
    sliding window algorithm for accurate rate limiting.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Rate Limiter
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_conn = redis.from_url(redis_url)
        self.rate_limits = {}
        self.last_requests = {}
        
        # Default rate limit configurations
        self.default_limits = {
            "npi_registry": RateLimitConfig(
                connector_name="npi_registry",
                requests_per_second=10.0,
                requests_per_minute=600,
                requests_per_hour=36000,
                burst_limit=20
            ),
            "google_places": RateLimitConfig(
                connector_name="google_places",
                requests_per_second=10.0,
                requests_per_minute=600,
                requests_per_hour=36000,
                burst_limit=20
            ),
            "google_document_ai": RateLimitConfig(
                connector_name="google_document_ai",
                requests_per_second=10.0,
                requests_per_minute=600,
                requests_per_hour=36000,
                burst_limit=20
            ),
            "hospital_website": RateLimitConfig(
                connector_name="hospital_website",
                requests_per_second=0.5,
                requests_per_minute=30,
                requests_per_hour=1800,
                burst_limit=5
            ),
            "state_board": RateLimitConfig(
                connector_name="state_board",
                requests_per_second=0.5,
                requests_per_minute=30,
                requests_per_hour=1800,
                burst_limit=5
            ),
            "enrichment": RateLimitConfig(
                connector_name="enrichment",
                requests_per_second=2.0,
                requests_per_minute=120,
                requests_per_hour=7200,
                burst_limit=10
            )
        }
    
    def set_rate_limit(self, connector_name: str, config: RateLimitConfig):
        """
        Set rate limit configuration for a connector
        
        Args:
            connector_name: Connector name
            config: Rate limit configuration
        """
        self.rate_limits[connector_name] = config
        logger.info(f"Set rate limit for {connector_name}: {config.requests_per_second} req/s")
    
    async def check_rate_limit(self, connector_name: str) -> Tuple[bool, float]:
        """
        Check if request is allowed under rate limit
        
        Args:
            connector_name: Connector name
            
        Returns:
            Tuple of (is_allowed, wait_time)
        """
        try:
            config = self.rate_limits.get(connector_name)
            if not config:
                config = self.default_limits.get(connector_name)
                if not config:
                    logger.warning(f"No rate limit config for {connector_name}, allowing request")
                    return True, 0.0
            
            # Use sliding window algorithm
            current_time = time.time()
            window_start = current_time - config.window_size
            
            # Redis key for this connector
            key = f"rate_limit:{connector_name}"
            
            # Remove old entries
            self.redis_conn.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            current_count = self.redis_conn.zcard(key)
            
            # Check if under limit
            if current_count < config.requests_per_minute:
                # Add current request
                self.redis_conn.zadd(key, {str(current_time): current_time})
                self.redis_conn.expire(key, config.window_size)
                
                # Check per-second limit
                last_request_time = self.last_requests.get(connector_name, 0)
                time_since_last = current_time - last_request_time
                min_interval = 1.0 / config.requests_per_second
                
                if time_since_last < min_interval:
                    wait_time = min_interval - time_since_last
                    self.last_requests[connector_name] = current_time + wait_time
                    return False, wait_time
                
                self.last_requests[connector_name] = current_time
                return True, 0.0
            else:
                # Calculate wait time until oldest request expires
                oldest_requests = self.redis_conn.zrange(key, 0, 0, withscores=True)
                if oldest_requests:
                    oldest_time = oldest_requests[0][1]
                    wait_time = (oldest_time + config.window_size) - current_time
                    return False, max(0, wait_time)
                
                return False, config.window_size
        
        except Exception as e:
            logger.error(f"Rate limit check failed for {connector_name}: {str(e)}")
            # Default to allowing request on error
            return True, 0.0
    
    async def wait_for_rate_limit(self, connector_name: str):
        """
        Wait for rate limit to allow request
        
        Args:
            connector_name: Connector name
        """
        while True:
            is_allowed, wait_time = await self.check_rate_limit(connector_name)
            
            if is_allowed:
                break
            
            if wait_time > 0:
                logger.info(f"Rate limit exceeded for {connector_name}, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
    
    def get_rate_limit_status(self, connector_name: str) -> Dict[str, Any]:
        """
        Get current rate limit status for a connector
        
        Args:
            connector_name: Connector name
            
        Returns:
            Rate limit status information
        """
        try:
            config = self.rate_limits.get(connector_name)
            if not config:
                config = self.default_limits.get(connector_name)
                if not config:
                    return {"error": "No rate limit config found"}
            
            current_time = time.time()
            window_start = current_time - config.window_size
            key = f"rate_limit:{connector_name}"
            
            # Get current usage
            self.redis_conn.zremrangebyscore(key, 0, window_start)
            current_count = self.redis_conn.zcard(key)
            
            # Calculate usage percentage
            usage_percentage = (current_count / config.requests_per_minute) * 100
            
            return {
                "connector_name": connector_name,
                "current_usage": current_count,
                "limit": config.requests_per_minute,
                "usage_percentage": usage_percentage,
                "requests_per_second": config.requests_per_second,
                "burst_limit": config.burst_limit,
                "window_size": config.window_size,
                "last_request": self.last_requests.get(connector_name, 0),
                "time_until_reset": window_start + config.window_size - current_time
            }
        
        except Exception as e:
            logger.error(f"Failed to get rate limit status for {connector_name}: {str(e)}")
            return {"error": str(e)}


class RetryPolicy:
    """
    Retry Policy with exponential backoff and circuit breaker
    
    Implements retry logic with configurable policies, exponential backoff,
    and circuit breaker pattern for resilient error handling.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Retry Policy
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_conn = redis.from_url(redis_url)
        self.retry_configs = {}
        self.circuit_breakers = {}
        
        # Default retry configurations
        self.default_configs = {
            "npi_registry": RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_backoff=True,
                retry_on_errors=["ConnectionError", "TimeoutError", "HTTPError"]
            ),
            "google_places": RetryConfig(
                max_retries=3,
                base_delay=1.0,
                max_delay=30.0,
                exponential_backoff=True,
                retry_on_errors=["ConnectionError", "TimeoutError", "HTTPError"]
            ),
            "hospital_website": RetryConfig(
                max_retries=5,
                base_delay=2.0,
                max_delay=60.0,
                exponential_backoff=True,
                retry_on_errors=["ConnectionError", "TimeoutError", "HTTPError", "ValidationError"]
            ),
            "state_board": RetryConfig(
                max_retries=5,
                base_delay=2.0,
                max_delay=60.0,
                exponential_backoff=True,
                retry_on_errors=["ConnectionError", "TimeoutError", "HTTPError", "ValidationError"]
            ),
            "enrichment": RetryConfig(
                max_retries=3,
                base_delay=1.5,
                max_delay=45.0,
                exponential_backoff=True,
                retry_on_errors=["ConnectionError", "TimeoutError", "HTTPError"]
            )
        }
        
        # Circuit breaker configurations
        self.circuit_breaker_configs = {
            "npi_registry": CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0),
            "google_places": CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0),
            "hospital_website": CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120.0),
            "state_board": CircuitBreakerConfig(failure_threshold=3, recovery_timeout=120.0),
            "enrichment": CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60.0)
        }
    
    def set_retry_config(self, connector_name: str, config: RetryConfig):
        """
        Set retry configuration for a connector
        
        Args:
            connector_name: Connector name
            config: Retry configuration
        """
        self.retry_configs[connector_name] = config
        logger.info(f"Set retry config for {connector_name}: {config.max_retries} max retries")
    
    def set_circuit_breaker_config(self, connector_name: str, config: CircuitBreakerConfig):
        """
        Set circuit breaker configuration for a connector
        
        Args:
            connector_name: Connector name
            config: Circuit breaker configuration
        """
        self.circuit_breaker_configs[connector_name] = config
        logger.info(f"Set circuit breaker config for {connector_name}")
    
    async def execute_with_retry(self, 
                                connector_name: str,
                                func: Callable,
                                *args,
                                **kwargs) -> Any:
        """
        Execute function with retry policy
        
        Args:
            connector_name: Connector name
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
        """
        config = self.retry_configs.get(connector_name)
        if not config:
            config = self.default_configs.get(connector_name)
            if not config:
                config = RetryConfig()  # Use default config
        
        circuit_breaker_config = self.circuit_breaker_configs.get(connector_name)
        if not circuit_breaker_config:
            circuit_breaker_config = CircuitBreakerConfig()
        
        # Check circuit breaker
        if not await self._is_circuit_breaker_open(connector_name, circuit_breaker_config):
            logger.warning(f"Circuit breaker is open for {connector_name}")
            raise Exception(f"Circuit breaker is open for {connector_name}")
        
        last_exception = None
        
        for attempt in range(config.max_retries + 1):
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Reset circuit breaker on success
                await self._reset_circuit_breaker(connector_name)
                
                return result
            
            except Exception as e:
                last_exception = e
                
                # Check if error is retryable
                if not self._is_retryable_error(e, config.retry_on_errors):
                    logger.error(f"Non-retryable error for {connector_name}: {str(e)}")
                    raise e
                
                # Record failure in circuit breaker
                await self._record_circuit_breaker_failure(connector_name)
                
                if attempt < config.max_retries:
                    # Calculate delay
                    delay = self._calculate_delay(attempt, config)
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {connector_name}: {str(e)}. Retrying in {delay:.2f}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {config.max_retries} retries failed for {connector_name}")
        
        # All retries failed
        raise last_exception
    
    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """
        Calculate delay for retry attempt
        
        Args:
            attempt: Attempt number (0-based)
            config: Retry configuration
            
        Returns:
            Delay in seconds
        """
        if config.exponential_backoff:
            delay = config.base_delay * (2 ** attempt)
        else:
            delay = config.base_delay * (attempt + 1)
        
        return min(delay, config.max_delay)
    
    def _is_retryable_error(self, error: Exception, retry_on_errors: List[str]) -> bool:
        """
        Check if error is retryable
        
        Args:
            error: Exception to check
            retry_on_errors: List of retryable error types
            
        Returns:
            True if error is retryable
        """
        error_type = type(error).__name__
        return error_type in retry_on_errors
    
    async def _is_circuit_breaker_open(self, connector_name: str, config: CircuitBreakerConfig) -> bool:
        """
        Check if circuit breaker is open
        
        Args:
            connector_name: Connector name
            config: Circuit breaker configuration
            
        Returns:
            True if circuit breaker is open
        """
        try:
            key = f"circuit_breaker:{connector_name}"
            data = self.redis_conn.hgetall(key)
            
            if not data:
                return True  # Circuit breaker is closed (no data)
            
            failure_count = int(data.get(b'failure_count', 0))
            last_failure_time = float(data.get(b'last_failure_time', 0))
            state = data.get(b'state', b'closed').decode()
            
            current_time = time.time()
            
            if state == b'open':
                # Check if recovery timeout has passed
                if current_time - last_failure_time > config.recovery_timeout:
                    # Move to half-open state
                    self.redis_conn.hset(key, 'state', 'half_open')
                    self.redis_conn.hset(key, 'half_open_calls', 0)
                    return True
                else:
                    return False  # Circuit breaker is open
            
            elif state == 'half_open':
                # Check if half-open calls exceed limit
                half_open_calls = int(data.get(b'half_open_calls', 0))
                if half_open_calls >= config.half_open_max_calls:
                    return False  # Circuit breaker is open
                else:
                    return True  # Circuit breaker is half-open
            
            else:  # closed
                return True  # Circuit breaker is closed
        
        except Exception as e:
            logger.error(f"Failed to check circuit breaker for {connector_name}: {str(e)}")
            return True  # Default to allowing request on error
    
    async def _record_circuit_breaker_failure(self, connector_name: str):
        """
        Record failure in circuit breaker
        
        Args:
            connector_name: Connector name
        """
        try:
            key = f"circuit_breaker:{connector_name}"
            config = self.circuit_breaker_configs.get(connector_name, CircuitBreakerConfig())
            
            # Increment failure count
            failure_count = self.redis_conn.hincrby(key, 'failure_count', 1)
            current_time = time.time()
            
            # Update last failure time
            self.redis_conn.hset(key, 'last_failure_time', current_time)
            
            # Check if threshold exceeded
            if failure_count >= config.failure_threshold:
                self.redis_conn.hset(key, 'state', 'open')
                logger.warning(f"Circuit breaker opened for {connector_name} after {failure_count} failures")
            
            # Set expiration
            self.redis_conn.expire(key, int(config.recovery_timeout * 2))
        
        except Exception as e:
            logger.error(f"Failed to record circuit breaker failure for {connector_name}: {str(e)}")
    
    async def _reset_circuit_breaker(self, connector_name: str):
        """
        Reset circuit breaker on success
        
        Args:
            connector_name: Connector name
        """
        try:
            key = f"circuit_breaker:{connector_name}"
            data = self.redis_conn.hgetall(key)
            
            if data:
                state = data.get(b'state', b'closed').decode()
                
                if state == 'half_open':
                    # Increment half-open calls
                    half_open_calls = self.redis_conn.hincrby(key, 'half_open_calls', 1)
                    config = self.circuit_breaker_configs.get(connector_name, CircuitBreakerConfig())
                    
                    # If enough successful calls, close circuit breaker
                    if half_open_calls >= config.half_open_max_calls:
                        self.redis_conn.delete(key)
                        logger.info(f"Circuit breaker closed for {connector_name}")
                else:
                    # Reset failure count on success
                    self.redis_conn.hset(key, 'failure_count', 0)
        
        except Exception as e:
            logger.error(f"Failed to reset circuit breaker for {connector_name}: {str(e)}")
    
    def get_retry_status(self, connector_name: str) -> Dict[str, Any]:
        """
        Get retry status for a connector
        
        Args:
            connector_name: Connector name
            
        Returns:
            Retry status information
        """
        try:
            config = self.retry_configs.get(connector_name)
            if not config:
                config = self.default_configs.get(connector_name)
                if not config:
                    config = RetryConfig()
            
            circuit_breaker_config = self.circuit_breaker_configs.get(connector_name)
            if not circuit_breaker_config:
                circuit_breaker_config = CircuitBreakerConfig()
            
            # Get circuit breaker status
            key = f"circuit_breaker:{connector_name}"
            data = self.redis_conn.hgetall(key)
            
            circuit_breaker_status = {
                "state": "closed",
                "failure_count": 0,
                "last_failure_time": None,
                "half_open_calls": 0
            }
            
            if data:
                circuit_breaker_status.update({
                    "state": data.get(b'state', b'closed').decode(),
                    "failure_count": int(data.get(b'failure_count', 0)),
                    "last_failure_time": float(data.get(b'last_failure_time', 0)),
                    "half_open_calls": int(data.get(b'half_open_calls', 0))
                })
            
            return {
                "connector_name": connector_name,
                "retry_config": {
                    "max_retries": config.max_retries,
                    "base_delay": config.base_delay,
                    "max_delay": config.max_delay,
                    "exponential_backoff": config.exponential_backoff,
                    "retry_on_errors": config.retry_on_errors
                },
                "circuit_breaker_config": {
                    "failure_threshold": circuit_breaker_config.failure_threshold,
                    "recovery_timeout": circuit_breaker_config.recovery_timeout,
                    "half_open_max_calls": circuit_breaker_config.half_open_max_calls
                },
                "circuit_breaker_status": circuit_breaker_status
            }
        
        except Exception as e:
            logger.error(f"Failed to get retry status for {connector_name}: {str(e)}")
            return {"error": str(e)}


# Global instances
rate_limiter = RateLimiter()
retry_policy = RetryPolicy()


# Example usage and testing functions
async def example_rate_limiter():
    """
    Example function demonstrating rate limiter
    """
    print("=" * 60)
    print("🚦 RATE LIMITER EXAMPLE")
    print("=" * 60)
    
    # Test rate limiting
    connector_name = "npi_registry"
    
    print(f"\n📋 Testing rate limiting for {connector_name}")
    
    for i in range(15):  # Try to make 15 requests quickly
        is_allowed, wait_time = await rate_limiter.check_rate_limit(connector_name)
        
        if is_allowed:
            print(f"   Request {i+1}: ✅ ALLOWED")
        else:
            print(f"   Request {i+1}: ❌ BLOCKED (wait {wait_time:.2f}s)")
            await asyncio.sleep(wait_time)
        
        await asyncio.sleep(0.1)  # Small delay between requests
    
    # Get status
    status = rate_limiter.get_rate_limit_status(connector_name)
    print(f"\n📊 Rate Limit Status:")
    print(f"   Current Usage: {status['current_usage']}")
    print(f"   Limit: {status['limit']}")
    print(f"   Usage Percentage: {status['usage_percentage']:.1f}%")


async def example_retry_policy():
    """
    Example function demonstrating retry policy
    """
    print("\n" + "=" * 60)
    print("🔄 RETRY POLICY EXAMPLE")
    print("=" * 60)
    
    # Mock function that fails first few times
    call_count = 0
    
    async def mock_function():
        nonlocal call_count
        call_count += 1
        
        if call_count < 3:
            raise ConnectionError("Connection failed")
        else:
            return f"Success on attempt {call_count}"
    
    # Test retry policy
    connector_name = "npi_registry"
    
    print(f"\n📋 Testing retry policy for {connector_name}")
    
    try:
        result = await retry_policy.execute_with_retry(connector_name, mock_function)
        print(f"   Result: {result}")
        print(f"   Total attempts: {call_count}")
    except Exception as e:
        print(f"   Failed: {str(e)}")
    
    # Get status
    status = retry_policy.get_retry_status(connector_name)
    print(f"\n📊 Retry Policy Status:")
    print(f"   Max Retries: {status['retry_config']['max_retries']}")
    print(f"   Base Delay: {status['retry_config']['base_delay']}s")
    print(f"   Circuit Breaker State: {status['circuit_breaker_status']['state']}")


if __name__ == "__main__":
    # Run examples
    print("Rate Limiter and Retry Policy - Examples")
    print("To run examples:")
    print("1. Install dependencies: pip install redis")
    print("2. Start Redis server: redis-server")
    print("3. Run: python -c 'from utils.rate_limiter import example_rate_limiter, example_retry_policy; asyncio.run(example_rate_limiter()); asyncio.run(example_retry_policy())'")

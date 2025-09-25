"""
State Medical Board Mock Scraper

This module provides a modular scraper for state medical board websites
with configurable XPaths/CSS selectors, robot checks, and retry logic.
Includes a mock HTTP server for testing license verification responses.
"""

import asyncio
import logging
import json
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

from .base import BaseConnector, ConnectorResponse, TrustScore

logger = logging.getLogger(__name__)


class LicenseStatus(Enum):
    """Medical license status enumeration"""
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    INACTIVE = "inactive"
    PENDING = "pending"
    PROBATION = "probation"


@dataclass
class LicenseVerificationResult:
    """Result from license verification"""
    license_number: str
    provider_name: str
    license_status: LicenseStatus
    issue_date: Optional[str] = None
    expiry_date: Optional[str] = None
    specialty: Optional[str] = None
    board_actions: List[Dict[str, Any]] = None
    verification_date: Optional[datetime] = None
    source_url: Optional[str] = None
    confidence_score: float = 0.0


@dataclass
class ScrapingConfig:
    """Configuration for scraping a specific state medical board"""
    state_code: str
    state_name: str
    base_url: str
    search_url: str
    search_method: str = "POST"  # GET or POST
    search_params: Dict[str, str] = None
    selectors: Dict[str, str] = None
    robot_check_selectors: List[str] = None
    rate_limit_delay: float = 2.0  # seconds between requests
    max_retries: int = 3
    timeout: int = 30
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class StateBoardMockConnector(BaseConnector):
    """
    State Medical Board Mock Scraper
    
    Provides modular scraping capabilities for state medical board websites
    with configurable selectors, robot checks, and retry logic.
    """
    
    def __init__(self, config: ScrapingConfig):
        """
        Initialize State Board Mock Connector
        
        Args:
            config: Scraping configuration for the state medical board
        """
        super().__init__(
            name=f"state_board_{config.state_code.lower()}",
            base_url=config.base_url,
            api_key=None,  # No API key needed for scraping
            rate_limit_delay=config.rate_limit_delay,
            max_retries=config.max_retries
        )
        
        self.config = config
        self.session = None
        
        # Default selectors if not provided
        self.default_selectors = {
            "license_number": "input[name='license_number'], input[name='licensenum'], #license",
            "provider_name": ".provider-name, .physician-name, .name",
            "license_status": ".status, .license-status, .current-status",
            "issue_date": ".issue-date, .issued, .date-issued",
            "expiry_date": ".expiry-date, .expires, .date-expires",
            "specialty": ".specialty, .specialization, .practice-area",
            "board_actions": ".board-actions, .disciplinary-actions, .actions",
            "error_message": ".error, .message, .alert",
            "no_results": ".no-results, .not-found, .no-matches"
        }
        
        # Default robot check selectors
        self.default_robot_selectors = [
            "input[name='captcha']",
            ".captcha",
            "#captcha",
            "input[name='robot']",
            ".robot-check",
            "input[name='verification']"
        ]
    
    async def verify_license(self, license_number: str, provider_name: Optional[str] = None) -> ConnectorResponse:
        """
        Verify medical license with state medical board
        
        Args:
            license_number: Medical license number
            provider_name: Optional provider name for additional verification
            
        Returns:
            ConnectorResponse with license verification data and trust scores
        """
        try:
            await self._rate_limit()
            
            # Check for robot detection
            robot_detected = await self._check_robot_detection()
            if robot_detected:
                return ConnectorResponse(
                    success=False,
                    error="Robot detection triggered - cannot proceed with scraping",
                    data=None,
                    trust_scores=None
                )
            
            # Perform license verification
            verification_result = await self._scrape_license_info(license_number, provider_name)
            
            if verification_result and verification_result.confidence_score > 0.5:
                # Normalize the result
                normalized_data = self._normalize_license_data(verification_result)
                trust_scores = self._calculate_trust_scores(verification_result, "license_verification")
                
                return ConnectorResponse(
                    success=True,
                    data=normalized_data,
                    trust_scores=trust_scores,
                    source=f"state_board_{self.config.state_code.lower()}",
                    timestamp=datetime.utcnow()
                )
            else:
                return ConnectorResponse(
                    success=False,
                    error=f"License verification failed: Low confidence ({verification_result.confidence_score:.2f})",
                    data=None,
                    trust_scores=None
                )
                
        except Exception as e:
            logger.error(f"Error verifying license {license_number}: {str(e)}")
            return ConnectorResponse(
                success=False,
                error=f"License verification error: {str(e)}",
                data=None,
                trust_scores=None
            )
    
    async def _scrape_license_info(self, license_number: str, provider_name: Optional[str] = None) -> Optional[LicenseVerificationResult]:
        """
        Scrape license information from state medical board website
        
        Args:
            license_number: License number to search for
            provider_name: Optional provider name
            
        Returns:
            LicenseVerificationResult or None if failed
        """
        for attempt in range(self.max_retries + 1):
            try:
                # Initialize session if needed
                if not self.session:
                    self.session = httpx.AsyncClient(
                        timeout=self.config.timeout,
                        headers={"User-Agent": self.config.user_agent}
                    )
                
                # Perform search
                search_result = await self._perform_search(license_number, provider_name)
                
                if search_result:
                    # Parse the results
                    verification_result = await self._parse_search_results(search_result, license_number)
                    
                    if verification_result:
                        return verification_result
                
                # If no results, wait and retry
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    logger.warning(f"No results found, waiting {delay}s before retry {attempt + 1}")
                    await asyncio.sleep(delay)
                    continue
                
                return None
                
            except Exception as e:
                logger.error(f"Scraping error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries:
                    delay = self._calculate_backoff_delay(attempt)
                    await asyncio.sleep(delay)
                    continue
                return None
        
        return None
    
    async def _perform_search(self, license_number: str, provider_name: Optional[str] = None) -> Optional[str]:
        """
        Perform search on state medical board website
        
        Args:
            license_number: License number to search for
            provider_name: Optional provider name
            
        Returns:
            HTML content or None if failed
        """
        try:
            # Build search parameters
            search_params = self._build_search_params(license_number, provider_name)
            
            if self.config.search_method.upper() == "POST":
                response = await self.session.post(
                    self.config.search_url,
                    data=search_params,
                    headers={"User-Agent": self.config.user_agent}
                )
            else:
                response = await self.session.get(
                    self.config.search_url,
                    params=search_params,
                    headers={"User-Agent": self.config.user_agent}
                )
            
            if response.status_code == 200:
                return response.text
            else:
                logger.error(f"Search failed with status {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Search request failed: {str(e)}")
            return None
    
    def _build_search_params(self, license_number: str, provider_name: Optional[str] = None) -> Dict[str, str]:
        """
        Build search parameters based on configuration
        
        Args:
            license_number: License number
            provider_name: Optional provider name
            
        Returns:
            Dictionary of search parameters
        """
        if self.config.search_params:
            params = self.config.search_params.copy()
        else:
            params = {}
        
        # Add license number
        params["license_number"] = license_number
        params["licensenum"] = license_number
        params["license"] = license_number
        
        # Add provider name if provided
        if provider_name:
            params["provider_name"] = provider_name
            params["name"] = provider_name
            params["physician_name"] = provider_name
        
        return params
    
    async def _parse_search_results(self, html_content: str, license_number: str) -> Optional[LicenseVerificationResult]:
        """
        Parse search results from HTML content
        
        Args:
            html_content: HTML content from search results
            license_number: Original license number searched for
            
        Returns:
            LicenseVerificationResult or None if parsing failed
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Check for error messages
            if self._has_error_message(soup):
                return None
            
            # Check for no results
            if self._has_no_results(soup):
                return None
            
            # Extract license information
            license_info = self._extract_license_info(soup, license_number)
            
            if license_info:
                return license_info
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing search results: {str(e)}")
            return None
    
    def _extract_license_info(self, soup: BeautifulSoup, license_number: str) -> Optional[LicenseVerificationResult]:
        """
        Extract license information from parsed HTML
        
        Args:
            soup: BeautifulSoup parsed HTML
            license_number: License number
            
        Returns:
            LicenseVerificationResult or None
        """
        try:
            selectors = self.config.selectors or self.default_selectors
            
            # Extract provider name
            provider_name = self._extract_text_by_selector(soup, selectors.get("provider_name"))
            
            # Extract license status
            status_text = self._extract_text_by_selector(soup, selectors.get("license_status"))
            license_status = self._parse_license_status(status_text)
            
            # Extract dates
            issue_date = self._extract_text_by_selector(soup, selectors.get("issue_date"))
            expiry_date = self._extract_text_by_selector(soup, selectors.get("expiry_date"))
            
            # Extract specialty
            specialty = self._extract_text_by_selector(soup, selectors.get("specialty"))
            
            # Extract board actions
            board_actions = self._extract_board_actions(soup, selectors.get("board_actions"))
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence_score(
                license_number, provider_name, license_status, status_text
            )
            
            return LicenseVerificationResult(
                license_number=license_number,
                provider_name=provider_name or "Unknown",
                license_status=license_status,
                issue_date=issue_date,
                expiry_date=expiry_date,
                specialty=specialty,
                board_actions=board_actions,
                verification_date=datetime.utcnow(),
                source_url=self.config.search_url,
                confidence_score=confidence_score
            )
            
        except Exception as e:
            logger.error(f"Error extracting license info: {str(e)}")
            return None
    
    def _extract_text_by_selector(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        """
        Extract text using CSS selector or XPath
        
        Args:
            soup: BeautifulSoup parsed HTML
            selector: CSS selector or XPath
            
        Returns:
            Extracted text or None
        """
        if not selector:
            return None
        
        try:
            # Try CSS selector first
            elements = soup.select(selector)
            if elements:
                return elements[0].get_text(strip=True)
            
            # Try XPath if CSS selector fails
            if selector.startswith('/') or selector.startswith('./'):
                # This is a simplified XPath implementation
                # In production, you'd use lxml or similar
                return self._extract_by_xpath(soup, selector)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting text with selector '{selector}': {str(e)}")
            return None
    
    def _extract_by_xpath(self, soup: BeautifulSoup, xpath: str) -> Optional[str]:
        """
        Extract text using XPath (simplified implementation)
        
        Args:
            soup: BeautifulSoup parsed HTML
            xpath: XPath expression
            
        Returns:
            Extracted text or None
        """
        # This is a simplified XPath implementation
        # In production, you'd use lxml or similar for full XPath support
        try:
            # Convert simple XPath to CSS selector
            if xpath.startswith('//'):
                xpath = xpath[2:]  # Remove //
            
            # Handle simple XPath patterns
            if xpath.startswith('*[@'):
                # Handle attribute selectors
                match = re.search(r'\*\[@(\w+)="([^"]+)"\]', xpath)
                if match:
                    attr_name, attr_value = match.groups()
                    elements = soup.find_all(attrs={attr_name: attr_value})
                    if elements:
                        return elements[0].get_text(strip=True)
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting with XPath '{xpath}': {str(e)}")
            return None
    
    def _parse_license_status(self, status_text: Optional[str]) -> LicenseStatus:
        """
        Parse license status from text
        
        Args:
            status_text: Status text from website
            
        Returns:
            LicenseStatus enum value
        """
        if not status_text:
            return LicenseStatus.INACTIVE
        
        status_text = status_text.lower().strip()
        
        if any(word in status_text for word in ['active', 'current', 'valid', 'good']):
            return LicenseStatus.ACTIVE
        elif any(word in status_text for word in ['expired', 'expire', 'invalid']):
            return LicenseStatus.EXPIRED
        elif any(word in status_text for word in ['suspended', 'suspend']):
            return LicenseStatus.SUSPENDED
        elif any(word in status_text for word in ['revoked', 'revoke', 'cancelled']):
            return LicenseStatus.REVOKED
        elif any(word in status_text for word in ['pending', 'pending']):
            return LicenseStatus.PENDING
        elif any(word in status_text for word in ['probation', 'probationary']):
            return LicenseStatus.PROBATION
        else:
            return LicenseStatus.INACTIVE
    
    def _extract_board_actions(self, soup: BeautifulSoup, selector: Optional[str]) -> List[Dict[str, Any]]:
        """
        Extract board actions from HTML
        
        Args:
            soup: BeautifulSoup parsed HTML
            selector: CSS selector for board actions
            
        Returns:
            List of board actions
        """
        if not selector:
            return []
        
        try:
            elements = soup.select(selector)
            actions = []
            
            for element in elements:
                action_text = element.get_text(strip=True)
                if action_text and len(action_text) > 10:  # Filter out empty or very short actions
                    actions.append({
                        "description": action_text,
                        "date": self._extract_date_from_text(action_text),
                        "type": self._classify_action_type(action_text)
                    })
            
            return actions
            
        except Exception as e:
            logger.error(f"Error extracting board actions: {str(e)}")
            return []
    
    def _extract_date_from_text(self, text: str) -> Optional[str]:
        """
        Extract date from text using regex patterns
        
        Args:
            text: Text to extract date from
            
        Returns:
            Extracted date string or None
        """
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{4})\b',  # MM/DD/YYYY
            r'\b(\d{4}-\d{2}-\d{2})\b',      # YYYY-MM-DD
            r'\b(\d{1,2}-\d{1,2}-\d{4})\b',  # MM-DD-YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _classify_action_type(self, action_text: str) -> str:
        """
        Classify the type of board action
        
        Args:
            action_text: Action description text
            
        Returns:
            Action type classification
        """
        action_text = action_text.lower()
        
        if any(word in action_text for word in ['suspension', 'suspend']):
            return 'suspension'
        elif any(word in action_text for word in ['revocation', 'revoke']):
            return 'revocation'
        elif any(word in action_text for word in ['probation', 'probationary']):
            return 'probation'
        elif any(word in action_text for word in ['fine', 'penalty']):
            return 'fine'
        elif any(word in action_text for word in ['warning', 'reprimand']):
            return 'warning'
        else:
            return 'other'
    
    def _calculate_confidence_score(self, license_number: str, provider_name: Optional[str], 
                                  license_status: LicenseStatus, status_text: Optional[str]) -> float:
        """
        Calculate confidence score for verification result
        
        Args:
            license_number: License number
            provider_name: Provider name
            license_status: Parsed license status
            status_text: Raw status text
            
        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0
        
        # Base score for successful parsing
        score += 0.3
        
        # Bonus for having provider name
        if provider_name and provider_name != "Unknown":
            score += 0.2
        
        # Bonus for clear status text
        if status_text and len(status_text.strip()) > 0:
            score += 0.2
        
        # Bonus for active license (easier to verify)
        if license_status == LicenseStatus.ACTIVE:
            score += 0.2
        elif license_status in [LicenseStatus.SUSPENDED, LicenseStatus.REVOKED]:
            score += 0.1  # These are also clearly defined
        
        # Penalty for unclear status
        if not status_text or status_text.strip() == "":
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    async def _check_robot_detection(self) -> bool:
        """
        Check if robot detection is triggered
        
        Returns:
            True if robot detection is active, False otherwise
        """
        try:
            if not self.session:
                self.session = httpx.AsyncClient(
                    timeout=self.config.timeout,
                    headers={"User-Agent": self.config.user_agent}
                )
            
            # Check main page for robot detection
            response = await self.session.get(
                self.config.base_url,
                headers={"User-Agent": self.config.user_agent}
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check for robot detection indicators
                robot_selectors = self.config.robot_check_selectors or self.default_robot_selectors
                
                for selector in robot_selectors:
                    elements = soup.select(selector)
                    if elements:
                        logger.warning(f"Robot detection triggered by selector: {selector}")
                        return True
                
                # Check for common robot detection text
                robot_text_indicators = [
                    "robot", "captcha", "verification", "security check",
                    "access denied", "blocked", "suspicious activity"
                ]
                
                page_text = soup.get_text().lower()
                for indicator in robot_text_indicators:
                    if indicator in page_text:
                        logger.warning(f"Robot detection triggered by text: {indicator}")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking robot detection: {str(e)}")
            return False
    
    def _has_error_message(self, soup: BeautifulSoup) -> bool:
        """Check if page contains error message"""
        selectors = self.config.selectors or self.default_selectors
        error_selector = selectors.get("error_message")
        
        if error_selector:
            elements = soup.select(error_selector)
            return len(elements) > 0
        
        return False
    
    def _has_no_results(self, soup: BeautifulSoup) -> bool:
        """Check if page indicates no results found"""
        selectors = self.config.selectors or self.default_selectors
        no_results_selector = selectors.get("no_results")
        
        if no_results_selector:
            elements = soup.select(no_results_selector)
            return len(elements) > 0
        
        return False
    
    def _normalize_license_data(self, verification_result: LicenseVerificationResult) -> Dict[str, Any]:
        """
        Normalize license verification result to our schema
        
        Args:
            verification_result: License verification result
            
        Returns:
            Normalized license data
        """
        return {
            "license_number": verification_result.license_number,
            "provider_name": verification_result.provider_name,
            "license_status": verification_result.license_status.value,
            "issue_date": verification_result.issue_date,
            "expiry_date": verification_result.expiry_date,
            "specialty": verification_result.specialty,
            "board_actions": verification_result.board_actions or [],
            "verification_date": verification_result.verification_date.isoformat() if verification_result.verification_date else None,
            "source_url": verification_result.source_url,
            "confidence_score": verification_result.confidence_score,
            "state_code": self.config.state_code,
            "state_name": self.config.state_name
        }
    
    def _calculate_trust_scores(self, verification_result: LicenseVerificationResult, source_type: str) -> Dict[str, TrustScore]:
        """
        Calculate trust scores for license verification results
        
        Args:
            verification_result: License verification result
            source_type: Type of verification performed
            
        Returns:
            Dictionary of field trust scores
        """
        trust_scores = {}
        
        # Base confidence for state medical board data (medium-high reliability)
        base_trust = 0.80
        
        # License number - high trust (direct match)
        trust_scores["license_number"] = TrustScore(
            score=0.95,
            reason="Direct license number match",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="high"
        )
        
        # License status - high trust
        trust_scores["license_status"] = TrustScore(
            score=base_trust,
            reason="Official state medical board status",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="high"
        )
        
        # Provider name - medium-high trust
        trust_scores["provider_name"] = TrustScore(
            score=0.75,
            reason="Provider name from state board",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="medium"
        )
        
        # Dates - medium trust (may be formatted differently)
        trust_scores["issue_date"] = TrustScore(
            score=0.70,
            reason="Issue date from state board",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="medium"
        )
        
        trust_scores["expiry_date"] = TrustScore(
            score=0.70,
            reason="Expiry date from state board",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="medium"
        )
        
        # Specialty - medium trust
        trust_scores["specialty"] = TrustScore(
            score=0.65,
            reason="Specialty information from state board",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="medium"
        )
        
        # Board actions - high trust (official disciplinary records)
        trust_scores["board_actions"] = TrustScore(
            score=0.90,
            reason="Official board disciplinary actions",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="high"
        )
        
        # Confidence score - reflects overall verification quality
        trust_scores["confidence_score"] = TrustScore(
            score=verification_result.confidence_score,
            reason="Overall verification confidence",
            source=f"state_board_{self.config.state_code.lower()}",
            confidence="high" if verification_result.confidence_score > 0.8 else "medium"
        )
        
        return trust_scores
    
    def _calculate_backoff_delay(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        base_delay = self.config.rate_limit_delay
        delay = base_delay * (2 ** attempt)
        return min(delay, 30.0)  # Max 30 seconds
    
    async def close(self):
        """Close the HTTP session"""
        if self.session:
            await self.session.aclose()
            self.session = None


# Mock HTTP Server for Testing
class MockStateBoardServer:
    """
    Mock HTTP server for testing state medical board scraping
    """
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server = None
        self.mock_data = self._generate_mock_data()
    
    def _generate_mock_data(self) -> Dict[str, Dict[str, Any]]:
        """Generate mock license verification data"""
        return {
            "A123456": {
                "license_number": "A123456",
                "provider_name": "Dr. John Smith",
                "license_status": "active",
                "issue_date": "2020-01-15",
                "expiry_date": "2025-01-15",
                "specialty": "Internal Medicine",
                "board_actions": [],
                "confidence_score": 0.95
            },
            "B789012": {
                "license_number": "B789012",
                "provider_name": "Dr. Jane Doe",
                "license_status": "suspended",
                "issue_date": "2018-06-01",
                "expiry_date": "2024-06-01",
                "specialty": "Family Medicine",
                "board_actions": [
                    {
                        "description": "Suspension for 6 months due to violation of medical standards",
                        "date": "2023-12-01",
                        "type": "suspension"
                    }
                ],
                "confidence_score": 0.90
            },
            "C345678": {
                "license_number": "C345678",
                "provider_name": "Dr. Robert Johnson",
                "license_status": "expired",
                "issue_date": "2015-03-10",
                "expiry_date": "2021-03-10",
                "specialty": "Pediatrics",
                "board_actions": [],
                "confidence_score": 0.85
            }
        }
    
    async def start_server(self):
        """Start the mock HTTP server"""
        from fastapi import FastAPI, Request, HTTPException
        from fastapi.responses import HTMLResponse
        import uvicorn
        
        app = FastAPI()
        
        @app.get("/")
        async def home():
            return HTMLResponse("""
            <html>
                <head><title>Mock State Medical Board</title></head>
                <body>
                    <h1>State Medical Board License Verification</h1>
                    <form method="post" action="/search">
                        <label for="license_number">License Number:</label>
                        <input type="text" id="license_number" name="license_number" required>
                        <br><br>
                        <label for="provider_name">Provider Name (optional):</label>
                        <input type="text" id="provider_name" name="provider_name">
                        <br><br>
                        <button type="submit">Search</button>
                    </form>
                </body>
            </html>
            """)
        
        @app.post("/search")
        async def search_license(request: Request):
            form = await request.form()
            license_number = form.get("license_number", "").strip()
            provider_name = form.get("provider_name", "").strip()
            
            if license_number in self.mock_data:
                data = self.mock_data[license_number]
                
                # Generate HTML response
                html_content = f"""
                <html>
                    <head><title>License Verification Results</title></head>
                    <body>
                        <h1>License Verification Results</h1>
                        <div class="provider-name">{data['provider_name']}</div>
                        <div class="license-status">Status: {data['license_status'].title()}</div>
                        <div class="issue-date">Issued: {data['issue_date']}</div>
                        <div class="expiry-date">Expires: {data['expiry_date']}</div>
                        <div class="specialty">Specialty: {data['specialty']}</div>
                        <div class="board-actions">
                            Board Actions: {len(data['board_actions'])} action(s)
                        </div>
                        <div class="confidence-score">Confidence: {data['confidence_score']:.2f}</div>
                    </body>
                </html>
                """
                
                return HTMLResponse(html_content)
            else:
                return HTMLResponse("""
                <html>
                    <head><title>No Results Found</title></head>
                    <body>
                        <h1>No Results Found</h1>
                        <div class="no-results">License number not found in our database.</div>
                    </body>
                </html>
                """, status_code=404)
        
        # Start server in background
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        await self.server.serve()
    
    async def stop_server(self):
        """Stop the mock HTTP server"""
        if self.server:
            self.server.should_exit = True


# Example usage and testing functions
async def example_state_board_scraping():
    """
    Example function demonstrating state board scraping
    """
    print("=" * 60)
    print("🏥 STATE MEDICAL BOARD SCRAPER EXAMPLE")
    print("=" * 60)
    
    # Create scraping configuration
    config = ScrapingConfig(
        state_code="CA",
        state_name="California",
        base_url="http://127.0.0.1:8080",
        search_url="http://127.0.0.1:8080/search",
        search_method="POST",
        search_params={
            "license_number": "license_number",
            "provider_name": "provider_name"
        },
        selectors={
            "provider_name": ".provider-name",
            "license_status": ".license-status",
            "issue_date": ".issue-date",
            "expiry_date": ".expiry-date",
            "specialty": ".specialty",
            "board_actions": ".board-actions",
            "no_results": ".no-results"
        },
        rate_limit_delay=1.0,
        max_retries=2
    )
    
    # Initialize connector
    connector = StateBoardMockConnector(config)
    
    try:
        # Example 1: Verify active license
        print("\n📋 Example 1: Active License Verification")
        print("-" * 40)
        
        result = await connector.verify_license("A123456", "Dr. John Smith")
        
        if result.success:
            print("✅ License verified successfully!")
            print(f"   License: {result.data['license_number']}")
            print(f"   Provider: {result.data['provider_name']}")
            print(f"   Status: {result.data['license_status']}")
            print(f"   Specialty: {result.data['specialty']}")
            print(f"   Expiry: {result.data['expiry_date']}")
            print(f"   Confidence: {result.data['confidence_score']:.2f}")
            
            print("\n📊 Trust Scores:")
            for field, trust in result.trust_scores.items():
                print(f"   {field:20}: {trust.score:.2f} - {trust.confidence}")
        else:
            print(f"❌ Error: {result.error}")
        
        # Example 2: Verify suspended license
        print("\n📋 Example 2: Suspended License Verification")
        print("-" * 40)
        
        result = await connector.verify_license("B789012", "Dr. Jane Doe")
        
        if result.success:
            print("✅ License verified successfully!")
            print(f"   License: {result.data['license_number']}")
            print(f"   Provider: {result.data['provider_name']}")
            print(f"   Status: {result.data['license_status']}")
            print(f"   Board Actions: {len(result.data['board_actions'])}")
            print(f"   Confidence: {result.data['confidence_score']:.2f}")
        else:
            print(f"❌ Error: {result.error}")
        
        # Example 3: Verify expired license
        print("\n📋 Example 3: Expired License Verification")
        print("-" * 40)
        
        result = await connector.verify_license("C345678", "Dr. Robert Johnson")
        
        if result.success:
            print("✅ License verified successfully!")
            print(f"   License: {result.data['license_number']}")
            print(f"   Provider: {result.data['provider_name']}")
            print(f"   Status: {result.data['license_status']}")
            print(f"   Expiry: {result.data['expiry_date']}")
            print(f"   Confidence: {result.data['confidence_score']:.2f}")
        else:
            print(f"❌ Error: {result.error}")
        
        # Example 4: Verify non-existent license
        print("\n📋 Example 4: Non-existent License")
        print("-" * 40)
        
        result = await connector.verify_license("X999999", "Dr. Non Existent")
        
        if result.success:
            print("✅ License verified successfully!")
        else:
            print(f"❌ Error: {result.error}")
    
    finally:
        await connector.close()


async def run_mock_server_example():
    """
    Example of running the mock server for testing
    """
    print("\n" + "=" * 60)
    print("🖥️  MOCK SERVER EXAMPLE")
    print("=" * 60)
    
    # Start mock server
    mock_server = MockStateBoardServer(port=8080)
    
    print("Starting mock server on http://127.0.0.1:8080")
    print("Available test licenses:")
    print("  • A123456 - Dr. John Smith (Active)")
    print("  • B789012 - Dr. Jane Doe (Suspended)")
    print("  • C345678 - Dr. Robert Johnson (Expired)")
    print("\nPress Ctrl+C to stop the server")
    
    try:
        await mock_server.start_server()
    except KeyboardInterrupt:
        print("\nStopping mock server...")
        await mock_server.stop_server()


if __name__ == "__main__":
    # Run examples
    print("State Medical Board Scraper - Examples")
    print("To run examples:")
    print("1. Start mock server: python -c 'from connectors.state_board_mock import run_mock_server_example; asyncio.run(run_mock_server_example())'")
    print("2. Run scraper example: python -c 'from connectors.state_board_mock import example_state_board_scraping; asyncio.run(example_state_board_scraping())'")

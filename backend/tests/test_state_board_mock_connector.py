"""
Tests for State Board Mock Connector
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
import httpx
from bs4 import BeautifulSoup

from connectors.state_board_mock import (
    StateBoardMockConnector, 
    ScrapingConfig, 
    LicenseStatus, 
    LicenseVerificationResult,
    MockStateBoardServer
)


class TestStateBoardMockConnector:
    """Test cases for State Board Mock Connector"""

    @pytest.fixture
    def scraping_config(self):
        """Create scraping configuration for testing"""
        return ScrapingConfig(
            state_code="CA",
            state_name="California",
            base_url="https://example-medical-board.com",
            search_url="https://example-medical-board.com/search",
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
                "error_message": ".error",
                "no_results": ".no-results"
            },
            rate_limit_delay=1.0,
            max_retries=2,
            timeout=30
        )

    @pytest.fixture
    def state_board_connector(self, scraping_config):
        """Create state board connector instance for testing"""
        return StateBoardMockConnector(scraping_config)

    @pytest.fixture
    def sample_html_response(self):
        """Sample HTML response from medical board website"""
        return """
        <html>
            <head><title>License Verification Results</title></head>
            <body>
                <div class="provider-name">Dr. John Smith</div>
                <div class="license-status">Status: Active</div>
                <div class="issue-date">Issued: 2020-01-15</div>
                <div class="expiry-date">Expires: 2025-01-15</div>
                <div class="specialty">Specialty: Internal Medicine</div>
                <div class="board-actions">Board Actions: 0 action(s)</div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_no_results(self):
        """Sample HTML response with no results"""
        return """
        <html>
            <head><title>No Results Found</title></head>
            <body>
                <div class="no-results">License number not found in our database.</div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_html_error(self):
        """Sample HTML response with error"""
        return """
        <html>
            <head><title>Error</title></head>
            <body>
                <div class="error">Invalid license number format.</div>
            </body>
        </html>
        """

    def test_connector_initialization(self, state_board_connector, scraping_config):
        """Test state board connector initialization"""
        assert state_board_connector.name == "state_board_ca"
        assert state_board_connector.base_url == scraping_config.base_url
        assert state_board_connector.config == scraping_config
        assert state_board_connector.session is None

    def test_parse_license_status(self, state_board_connector):
        """Test license status parsing"""
        assert state_board_connector._parse_license_status("Active") == LicenseStatus.ACTIVE
        assert state_board_connector._parse_license_status("Current") == LicenseStatus.ACTIVE
        assert state_board_connector._parse_license_status("Valid") == LicenseStatus.ACTIVE
        assert state_board_connector._parse_license_status("Expired") == LicenseStatus.EXPIRED
        assert state_board_connector._parse_license_status("Suspended") == LicenseStatus.SUSPENDED
        assert state_board_connector._parse_license_status("Revoked") == LicenseStatus.REVOKED
        assert state_board_connector._parse_license_status("Pending") == LicenseStatus.PENDING
        assert state_board_connector._parse_license_status("Probation") == LicenseStatus.PROBATION
        assert state_board_connector._parse_license_status("Unknown") == LicenseStatus.INACTIVE
        assert state_board_connector._parse_license_status(None) == LicenseStatus.INACTIVE

    def test_extract_text_by_selector(self, state_board_connector, sample_html_response):
        """Test text extraction using CSS selectors"""
        soup = BeautifulSoup(sample_html_response, 'html.parser')
        
        # Test successful extraction
        text = state_board_connector._extract_text_by_selector(soup, ".provider-name")
        assert text == "Dr. John Smith"
        
        text = state_board_connector._extract_text_by_selector(soup, ".license-status")
        assert text == "Status: Active"
        
        text = state_board_connector._extract_text_by_selector(soup, ".specialty")
        assert text == "Specialty: Internal Medicine"
        
        # Test non-existent selector
        text = state_board_connector._extract_text_by_selector(soup, ".non-existent")
        assert text is None
        
        # Test empty selector
        text = state_board_connector._extract_text_by_selector(soup, "")
        assert text is None

    def test_extract_date_from_text(self, state_board_connector):
        """Test date extraction from text"""
        # Test various date formats
        assert state_board_connector._extract_date_from_text("Issued: 01/15/2020") == "01/15/2020"
        assert state_board_connector._extract_date_from_text("Expires: 2025-01-15") == "2025-01-15"
        assert state_board_connector._extract_date_from_text("Date: 12-25-2023") == "12-25-2023"
        
        # Test text without dates
        assert state_board_connector._extract_date_from_text("No date here") is None
        assert state_board_connector._extract_date_from_text("") is None

    def test_classify_action_type(self, state_board_connector):
        """Test board action type classification"""
        assert state_board_connector._classify_action_type("Suspension for 6 months") == "suspension"
        assert state_board_connector._classify_action_type("License revoked") == "revocation"
        assert state_board_connector._classify_action_type("Probationary period") == "probation"
        assert state_board_connector._classify_action_type("Fine of $5000") == "fine"
        assert state_board_connector._classify_action_type("Warning issued") == "warning"
        assert state_board_connector._classify_action_type("Other action") == "other"

    def test_extract_board_actions(self, state_board_connector):
        """Test board actions extraction"""
        html_with_actions = """
        <html>
            <body>
                <div class="board-actions">
                    <div>Suspension for 6 months due to violation of medical standards (12/01/2023)</div>
                    <div>Fine of $5000 for administrative violation (06/15/2023)</div>
                </div>
            </body>
        </html>
        """
        
        soup = BeautifulSoup(html_with_actions, 'html.parser')
        actions = state_board_connector._extract_board_actions(soup, ".board-actions")
        
        assert len(actions) == 2
        assert actions[0]["description"] == "Suspension for 6 months due to violation of medical standards (12/01/2023)"
        assert actions[0]["type"] == "suspension"
        assert actions[1]["description"] == "Fine of $5000 for administrative violation (06/15/2023)"
        assert actions[1]["type"] == "fine"

    def test_calculate_confidence_score(self, state_board_connector):
        """Test confidence score calculation"""
        # High confidence scenario
        score = state_board_connector._calculate_confidence_score(
            "A123456", "Dr. John Smith", LicenseStatus.ACTIVE, "Active"
        )
        assert score > 0.8
        
        # Medium confidence scenario
        score = state_board_connector._calculate_confidence_score(
            "B789012", "Dr. Jane Doe", LicenseStatus.SUSPENDED, "Suspended"
        )
        assert 0.6 <= score <= 0.8
        
        # Low confidence scenario
        score = state_board_connector._calculate_confidence_score(
            "C345678", "Unknown", LicenseStatus.INACTIVE, ""
        )
        assert score < 0.6

    def test_build_search_params(self, state_board_connector):
        """Test search parameters building"""
        params = state_board_connector._build_search_params("A123456", "Dr. John Smith")
        
        assert params["license_number"] == "A123456"
        assert params["provider_name"] == "Dr. John Smith"
        assert params["licensenum"] == "A123456"
        assert params["name"] == "Dr. John Smith"
        
        # Test without provider name
        params = state_board_connector._build_search_params("B789012")
        assert params["license_number"] == "B789012"
        assert "provider_name" not in params

    def test_has_error_message(self, state_board_connector, sample_html_error):
        """Test error message detection"""
        soup = BeautifulSoup(sample_html_error, 'html.parser')
        assert state_board_connector._has_error_message(soup) == True
        
        soup = BeautifulSoup(sample_html_response, 'html.parser')
        assert state_board_connector._has_error_message(soup) == False

    def test_has_no_results(self, state_board_connector, sample_html_no_results):
        """Test no results detection"""
        soup = BeautifulSoup(sample_html_no_results, 'html.parser')
        assert state_board_connector._has_no_results(soup) == True
        
        soup = BeautifulSoup(sample_html_response, 'html.parser')
        assert state_board_connector._has_no_results(soup) == False

    def test_calculate_backoff_delay(self, state_board_connector):
        """Test backoff delay calculation"""
        assert state_board_connector._calculate_backoff_delay(0) == 1.0  # base_delay
        assert state_board_connector._calculate_backoff_delay(1) == 2.0  # base_delay * 2
        assert state_board_connector._calculate_backoff_delay(2) == 4.0  # base_delay * 4
        assert state_board_connector._calculate_backoff_delay(10) == 30.0  # max_delay

    @pytest.mark.asyncio
    async def test_verify_license_success(self, state_board_connector, sample_html_response):
        """Test successful license verification"""
        with patch.object(state_board_connector, '_check_robot_detection', return_value=False):
            with patch.object(state_board_connector, '_scrape_license_info') as mock_scrape:
                # Mock successful scraping result
                mock_result = LicenseVerificationResult(
                    license_number="A123456",
                    provider_name="Dr. John Smith",
                    license_status=LicenseStatus.ACTIVE,
                    issue_date="2020-01-15",
                    expiry_date="2025-01-15",
                    specialty="Internal Medicine",
                    board_actions=[],
                    verification_date=datetime.utcnow(),
                    source_url="https://example-medical-board.com/search",
                    confidence_score=0.95
                )
                mock_scrape.return_value = mock_result
                
                result = await state_board_connector.verify_license("A123456", "Dr. John Smith")
                
                assert result.success == True
                assert result.data is not None
                assert result.data["license_number"] == "A123456"
                assert result.data["provider_name"] == "Dr. John Smith"
                assert result.data["license_status"] == "active"
                assert result.trust_scores is not None
                assert result.source == "state_board_ca"

    @pytest.mark.asyncio
    async def test_verify_license_robot_detection(self, state_board_connector):
        """Test license verification with robot detection"""
        with patch.object(state_board_connector, '_check_robot_detection', return_value=True):
            result = await state_board_connector.verify_license("A123456", "Dr. John Smith")
            
            assert result.success == False
            assert "Robot detection triggered" in result.error
            assert result.data is None

    @pytest.mark.asyncio
    async def test_verify_license_low_confidence(self, state_board_connector):
        """Test license verification with low confidence"""
        with patch.object(state_board_connector, '_check_robot_detection', return_value=False):
            with patch.object(state_board_connector, '_scrape_license_info') as mock_scrape:
                # Mock low confidence result
                mock_result = LicenseVerificationResult(
                    license_number="A123456",
                    provider_name="Unknown",
                    license_status=LicenseStatus.INACTIVE,
                    confidence_score=0.3
                )
                mock_scrape.return_value = mock_result
                
                result = await state_board_connector.verify_license("A123456")
                
                assert result.success == False
                assert "Low confidence" in result.error

    @pytest.mark.asyncio
    async def test_verify_license_scraping_error(self, state_board_connector):
        """Test license verification with scraping error"""
        with patch.object(state_board_connector, '_check_robot_detection', return_value=False):
            with patch.object(state_board_connector, '_scrape_license_info', side_effect=Exception("Scraping error")):
                result = await state_board_connector.verify_license("A123456")
                
                assert result.success == False
                assert "License verification error" in result.error

    @pytest.mark.asyncio
    async def test_scrape_license_info_success(self, state_board_connector, sample_html_response):
        """Test successful license info scraping"""
        with patch.object(state_board_connector, '_perform_search', return_value=sample_html_response):
            with patch.object(state_board_connector, '_parse_search_results') as mock_parse:
                mock_result = LicenseVerificationResult(
                    license_number="A123456",
                    provider_name="Dr. John Smith",
                    license_status=LicenseStatus.ACTIVE,
                    confidence_score=0.95
                )
                mock_parse.return_value = mock_result
                
                result = await state_board_connector._scrape_license_info("A123456", "Dr. John Smith")
                
                assert result is not None
                assert result.license_number == "A123456"
                assert result.provider_name == "Dr. John Smith"

    @pytest.mark.asyncio
    async def test_scrape_license_info_no_results(self, state_board_connector):
        """Test license info scraping with no results"""
        with patch.object(state_board_connector, '_perform_search', return_value=None):
            result = await state_board_connector._scrape_license_info("A123456")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_perform_search_post(self, state_board_connector):
        """Test POST search request"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test response</html>"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = AsyncMock()
            mock_session.post.return_value = mock_response
            mock_client.return_value = mock_session
            
            state_board_connector.session = mock_session
            result = await state_board_connector._perform_search("A123456", "Dr. John Smith")
            
            assert result == "<html>Test response</html>"
            mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_search_get(self, scraping_config):
        """Test GET search request"""
        scraping_config.search_method = "GET"
        connector = StateBoardMockConnector(scraping_config)
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html>Test response</html>"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_response
            mock_client.return_value = mock_session
            
            connector.session = mock_session
            result = await connector._perform_search("A123456")
            
            assert result == "<html>Test response</html>"
            mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_search_results_success(self, state_board_connector, sample_html_response):
        """Test successful search results parsing"""
        result = await state_board_connector._parse_search_results(sample_html_response, "A123456")
        
        # This should return a LicenseVerificationResult
        assert result is not None
        assert isinstance(result, LicenseVerificationResult)

    @pytest.mark.asyncio
    async def test_parse_search_results_error(self, state_board_connector, sample_html_error):
        """Test search results parsing with error"""
        result = await state_board_connector._parse_search_results(sample_html_error, "A123456")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_parse_search_results_no_results(self, state_board_connector, sample_html_no_results):
        """Test search results parsing with no results"""
        result = await state_board_connector._parse_search_results(sample_html_no_results, "A123456")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_check_robot_detection_no_robot(self, state_board_connector):
        """Test robot detection check with no robot detection"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Normal page</body></html>"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_response
            mock_client.return_value = mock_session
            
            state_board_connector.session = mock_session
            result = await state_board_connector._check_robot_detection()
            
            assert result == False

    @pytest.mark.asyncio
    async def test_check_robot_detection_with_robot(self, state_board_connector):
        """Test robot detection check with robot detection"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body><input name='captcha' /></body></html>"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_session = AsyncMock()
            mock_session.get.return_value = mock_response
            mock_client.return_value = mock_session
            
            state_board_connector.session = mock_session
            result = await state_board_connector._check_robot_detection()
            
            assert result == True

    def test_normalize_license_data(self, state_board_connector):
        """Test license data normalization"""
        verification_result = LicenseVerificationResult(
            license_number="A123456",
            provider_name="Dr. John Smith",
            license_status=LicenseStatus.ACTIVE,
            issue_date="2020-01-15",
            expiry_date="2025-01-15",
            specialty="Internal Medicine",
            board_actions=[],
            verification_date=datetime.utcnow(),
            source_url="https://example-medical-board.com/search",
            confidence_score=0.95
        )
        
        normalized = state_board_connector._normalize_license_data(verification_result)
        
        assert normalized["license_number"] == "A123456"
        assert normalized["provider_name"] == "Dr. John Smith"
        assert normalized["license_status"] == "active"
        assert normalized["issue_date"] == "2020-01-15"
        assert normalized["expiry_date"] == "2025-01-15"
        assert normalized["specialty"] == "Internal Medicine"
        assert normalized["board_actions"] == []
        assert normalized["confidence_score"] == 0.95
        assert normalized["state_code"] == "CA"
        assert normalized["state_name"] == "California"

    def test_calculate_trust_scores(self, state_board_connector):
        """Test trust score calculation"""
        verification_result = LicenseVerificationResult(
            license_number="A123456",
            provider_name="Dr. John Smith",
            license_status=LicenseStatus.ACTIVE,
            confidence_score=0.95
        )
        
        trust_scores = state_board_connector._calculate_trust_scores(verification_result, "license_verification")
        
        # Check high-trust fields
        assert trust_scores["license_number"].score == 0.95
        assert trust_scores["license_status"].score == 0.80
        assert trust_scores["board_actions"].score == 0.90
        
        # Check medium-trust fields
        assert trust_scores["provider_name"].score == 0.75
        assert trust_scores["issue_date"].score == 0.70
        assert trust_scores["expiry_date"].score == 0.70
        assert trust_scores["specialty"].score == 0.65
        
        # Check confidence score
        assert trust_scores["confidence_score"].score == 0.95

    @pytest.mark.asyncio
    async def test_close_session(self, state_board_connector):
        """Test session cleanup"""
        mock_session = AsyncMock()
        state_board_connector.session = mock_session
        
        await state_board_connector.close()
        
        mock_session.aclose.assert_called_once()
        assert state_board_connector.session is None


class TestMockStateBoardServer:
    """Test cases for Mock State Board Server"""

    def test_mock_server_initialization(self):
        """Test mock server initialization"""
        server = MockStateBoardServer(port=8080)
        
        assert server.port == 8080
        assert server.server is None
        assert server.mock_data is not None
        assert "A123456" in server.mock_data
        assert "B789012" in server.mock_data
        assert "C345678" in server.mock_data

    def test_generate_mock_data(self):
        """Test mock data generation"""
        server = MockStateBoardServer()
        mock_data = server._generate_mock_data()
        
        # Check that all test licenses are present
        assert "A123456" in mock_data
        assert "B789012" in mock_data
        assert "C345678" in mock_data
        
        # Check data structure
        license_data = mock_data["A123456"]
        assert license_data["license_number"] == "A123456"
        assert license_data["provider_name"] == "Dr. John Smith"
        assert license_data["license_status"] == "active"
        assert license_data["confidence_score"] == 0.95
        
        # Check suspended license data
        suspended_data = mock_data["B789012"]
        assert suspended_data["license_status"] == "suspended"
        assert len(suspended_data["board_actions"]) > 0


if __name__ == "__main__":
    # Run basic tests
    pytest.main([__file__, "-v"])

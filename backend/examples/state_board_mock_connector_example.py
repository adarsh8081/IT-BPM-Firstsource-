"""
State Board Mock Connector Example Usage

This script demonstrates how to use the state board mock connector to scrape
medical board websites and shows example API calls and responses.
"""

import asyncio
import json
from datetime import datetime
from connectors.state_board_mock import (
    StateBoardMockConnector, 
    ScrapingConfig, 
    LicenseStatus,
    MockStateBoardServer
)


async def example_state_board_scraping():
    """
    Example: Scrape state medical board for license verification
    """
    print("=" * 60)
    print("🏥 STATE MEDICAL BOARD SCRAPER EXAMPLE")
    print("=" * 60)
    
    # Create scraping configuration for California Medical Board
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
        robot_check_selectors=[
            "input[name='captcha']",
            ".captcha",
            "#captcha"
        ],
        rate_limit_delay=1.0,
        max_retries=2,
        timeout=30
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
            print(f"   Issue Date: {result.data['issue_date']}")
            print(f"   Expiry Date: {result.data['expiry_date']}")
            print(f"   Board Actions: {len(result.data['board_actions'])}")
            print(f"   Confidence: {result.data['confidence_score']:.2f}")
            
            print("\n📊 Trust Scores:")
            for field, trust in result.trust_scores.items():
                print(f"   {field:20}: {trust.score:.2f} - {trust.confidence}")
                print(f"   {'':20}   {trust.reason}")
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
            print(f"   Specialty: {result.data['specialty']}")
            print(f"   Board Actions: {len(result.data['board_actions'])}")
            if result.data['board_actions']:
                print("   Recent Actions:")
                for action in result.data['board_actions'][:2]:  # Show first 2 actions
                    print(f"     • {action['description']}")
                    print(f"       Date: {action['date']}, Type: {action['type']}")
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
            print(f"   Specialty: {result.data['specialty']}")
            print(f"   Issue Date: {result.data['issue_date']}")
            print(f"   Expiry Date: {result.data['expiry_date']}")
            print(f"   Board Actions: {len(result.data['board_actions'])}")
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
        
        # Example 5: Robot detection scenario
        print("\n📋 Example 5: Robot Detection Handling")
        print("-" * 40)
        
        # This would normally trigger robot detection in a real scenario
        print("   Robot detection is automatically handled by the connector")
        print("   The connector checks for common robot detection indicators:")
        print("   • CAPTCHA forms")
        print("   • Security check pages")
        print("   • Access denied messages")
        print("   • Suspicious activity warnings")
    
    finally:
        await connector.close()


async def example_different_state_configs():
    """
    Example: Different state medical board configurations
    """
    print("\n" + "=" * 60)
    print("📋 Example 6: Different State Configurations")
    print("=" * 60)
    
    # Texas Medical Board configuration
    tx_config = ScrapingConfig(
        state_code="TX",
        state_name="Texas",
        base_url="https://www.tmb.state.tx.us",
        search_url="https://www.tmb.state.tx.us/page/physician-profile-search",
        search_method="GET",
        search_params={
            "license_number": "lic",
            "provider_name": "name"
        },
        selectors={
            "provider_name": ".physician-name",
            "license_status": ".license-status",
            "issue_date": ".date-issued",
            "expiry_date": ".date-expires",
            "specialty": ".specialty",
            "board_actions": ".disciplinary-actions"
        },
        rate_limit_delay=2.0,
        max_retries=3
    )
    
    # New York Medical Board configuration
    ny_config = ScrapingConfig(
        state_code="NY",
        state_name="New York",
        base_url="https://www.op.nysed.gov",
        search_url="https://www.op.nysed.gov/prof/med/medlic.htm",
        search_method="POST",
        search_params={
            "license_number": "licensenum",
            "provider_name": "name"
        },
        selectors={
            "provider_name": ".name",
            "license_status": ".status",
            "issue_date": ".issued",
            "expiry_date": ".expires",
            "specialty": ".specialization",
            "board_actions": ".actions"
        },
        rate_limit_delay=1.5,
        max_retries=2
    )
    
    print("📋 Texas Medical Board Configuration:")
    print(f"   State: {tx_config.state_name} ({tx_config.state_code})")
    print(f"   Base URL: {tx_config.base_url}")
    print(f"   Search Method: {tx_config.search_method}")
    print(f"   Rate Limit: {tx_config.rate_limit_delay}s")
    print(f"   Max Retries: {tx_config.max_retries}")
    
    print("\n📋 New York Medical Board Configuration:")
    print(f"   State: {ny_config.state_name} ({ny_config.state_code})")
    print(f"   Base URL: {ny_config.base_url}")
    print(f"   Search Method: {ny_config.search_method}")
    print(f"   Rate Limit: {ny_config.rate_limit_delay}s")
    print(f"   Max Retries: {ny_config.max_retries}")


async def example_mock_server():
    """
    Example: Running the mock server for testing
    """
    print("\n" + "=" * 60)
    print("🖥️  Example 7: Mock Server for Testing")
    print("=" * 60)
    
    # Start mock server
    mock_server = MockStateBoardServer(port=8080)
    
    print("🚀 Starting mock server on http://127.0.0.1:8080")
    print("\n📋 Available test licenses:")
    print("   • A123456 - Dr. John Smith (Active)")
    print("   • B789012 - Dr. Jane Doe (Suspended)")
    print("   • C345678 - Dr. Robert Johnson (Expired)")
    
    print("\n🔍 Test the server manually:")
    print("   1. Open browser to http://127.0.0.1:8080")
    print("   2. Enter license number: A123456")
    print("   3. Enter provider name: Dr. John Smith")
    print("   4. Click Search to see results")
    
    print("\n⚠️  Press Ctrl+C to stop the server")
    
    try:
        await mock_server.start_server()
    except KeyboardInterrupt:
        print("\n🛑 Stopping mock server...")
        await mock_server.stop_server()
        print("✅ Mock server stopped")


def show_scraping_config_examples():
    """
    Show examples of different scraping configurations
    """
    print("\n" + "=" * 60)
    print("📋 Example 8: Scraping Configuration Examples")
    print("=" * 60)
    
    # Example 1: Basic configuration
    basic_config = {
        "state_code": "CA",
        "state_name": "California",
        "base_url": "https://www.mbc.ca.gov",
        "search_url": "https://www.mbc.ca.gov/breeze/license_lookup.php",
        "search_method": "POST",
        "selectors": {
            "provider_name": ".physician-name",
            "license_status": ".license-status",
            "issue_date": ".date-issued",
            "expiry_date": ".date-expires"
        }
    }
    
    # Example 2: Advanced configuration with robot detection
    advanced_config = {
        "state_code": "FL",
        "state_name": "Florida",
        "base_url": "https://www.flhealthsource.gov",
        "search_url": "https://www.flhealthsource.gov/mqa",
        "search_method": "GET",
        "selectors": {
            "provider_name": "#physician-name",
            "license_status": ".current-status",
            "issue_date": ".issue-date",
            "expiry_date": ".expiry-date",
            "specialty": ".specialty",
            "board_actions": ".disciplinary-actions"
        },
        "robot_check_selectors": [
            "input[name='captcha']",
            ".captcha",
            "#captcha",
            "input[name='robot']",
            ".robot-check"
        ],
        "rate_limit_delay": 2.0,
        "max_retries": 3,
        "timeout": 30
    }
    
    print("📋 Basic Configuration Example:")
    print(json.dumps(basic_config, indent=2))
    
    print("\n📋 Advanced Configuration Example:")
    print(json.dumps(advanced_config, indent=2))


def show_selector_examples():
    """
    Show examples of different selector types
    """
    print("\n" + "=" * 60)
    print("🎯 Example 9: Selector Examples")
    print("=" * 60)
    
    selector_examples = {
        "CSS Selectors": {
            "provider_name": ".physician-name",
            "license_status": "#license-status",
            "issue_date": "div.date-issued",
            "expiry_date": "span.expiry-date",
            "specialty": ".specialty-list li:first-child",
            "board_actions": ".actions table tr"
        },
        "XPath Selectors": {
            "provider_name": "//div[@class='physician-name']",
            "license_status": "//span[@id='license-status']",
            "issue_date": "//td[contains(text(), 'Issued')]/following-sibling::td",
            "expiry_date": "//td[contains(text(), 'Expires')]/following-sibling::td",
            "specialty": "//div[@class='specialty']//text()",
            "board_actions": "//table[@class='actions']//tr"
        },
        "Attribute Selectors": {
            "provider_name": "input[name='physician_name']",
            "license_status": "span[data-status='current']",
            "issue_date": "div[data-field='issue_date']",
            "expiry_date": "div[data-field='expiry_date']",
            "specialty": "select[name='specialty'] option[selected]",
            "board_actions": "div[class*='action']"
        }
    }
    
    for selector_type, selectors in selector_examples.items():
        print(f"\n📋 {selector_type}:")
        for field, selector in selectors.items():
            print(f"   {field:15}: {selector}")


def show_license_status_examples():
    """
    Show examples of different license statuses
    """
    print("\n" + "=" * 60)
    print("📋 Example 10: License Status Examples")
    print("=" * 60)
    
    status_examples = {
        "Active": {
            "text_variations": ["Active", "Current", "Valid", "Good Standing"],
            "description": "License is currently valid and active"
        },
        "Expired": {
            "text_variations": ["Expired", "Expire", "Invalid", "Lapsed"],
            "description": "License has expired and is no longer valid"
        },
        "Suspended": {
            "text_variations": ["Suspended", "Suspend", "Temporary Suspension"],
            "description": "License is temporarily suspended"
        },
        "Revoked": {
            "text_variations": ["Revoked", "Revoke", "Cancelled", "Terminated"],
            "description": "License has been permanently revoked"
        },
        "Pending": {
            "text_variations": ["Pending", "Pending Review", "Under Review"],
            "description": "License application or renewal is pending"
        },
        "Probation": {
            "text_variations": ["Probation", "Probationary", "On Probation"],
            "description": "License is on probationary status"
        }
    }
    
    for status, info in status_examples.items():
        print(f"\n📋 {status}:")
        print(f"   Description: {info['description']}")
        print(f"   Text Variations: {', '.join(info['text_variations'])}")


async def main():
    """
    Main function to run all examples
    """
    try:
        # Run examples
        await example_state_board_scraping()
        await example_different_state_configs()
        await example_mock_server()
        show_scraping_config_examples()
        show_selector_examples()
        show_license_status_examples()
        
        print("\n" + "=" * 60)
        print("✅ State Board Mock Connector Examples Complete!")
        print("=" * 60)
        print("\n📝 Key Features Demonstrated:")
        print("   ✅ Modular scraping with configurable selectors")
        print("   ✅ Robot detection and handling")
        print("   ✅ Rate limiting and exponential backoff")
        print("   ✅ License status parsing and classification")
        print("   ✅ Board actions extraction and classification")
        print("   ✅ Confidence scoring and trust evaluation")
        print("   ✅ Mock server for testing")
        print("   ✅ Multiple state configurations")
        print("   ✅ CSS and XPath selector support")
        
        print("\n🔧 Configuration Options:")
        print("   • State-specific scraping configurations")
        print("   • Custom CSS selectors and XPath expressions")
        print("   • Robot detection selectors")
        print("   • Rate limiting and retry settings")
        print("   • Timeout and user agent configuration")
        
        print("\n⚠️  Important Notes:")
        print("   • Always respect robots.txt and website terms")
        print("   • Implement appropriate rate limiting")
        print("   • Handle robot detection gracefully")
        print("   • Monitor for website changes")
        print("   • Use mock server for testing")
        
    except Exception as e:
        print(f"❌ Error running examples: {e}")


if __name__ == "__main__":
    # Run examples
    print("State Board Mock Connector - Examples")
    print("To run examples:")
    print("1. Start mock server: python -c 'from connectors.state_board_mock import example_mock_server; asyncio.run(example_mock_server())'")
    print("2. Run scraper example: python -c 'from connectors.state_board_mock import example_state_board_scraping; asyncio.run(example_state_board_scraping())'")
    print("3. Run all examples: python -c 'from connectors.state_board_mock import main; asyncio.run(main())'")

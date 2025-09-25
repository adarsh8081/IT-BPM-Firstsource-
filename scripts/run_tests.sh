#!/bin/bash

# Test Runner Script for Provider Validation Application
# This script runs all test suites with proper configuration

set -e

echo "🧪 Running Provider Validation Application Tests"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command_exists python3; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

if ! command_exists node; then
    print_error "Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    print_error "npm is required but not installed"
    exit 1
fi

print_success "Prerequisites check passed"

# Parse command line arguments
RUN_UNIT=true
RUN_INTEGRATION=true
RUN_E2E=true
RUN_PERFORMANCE=false
RUN_FUZZ=false
VERBOSE=false
COVERAGE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit-only)
            RUN_UNIT=true
            RUN_INTEGRATION=false
            RUN_E2E=false
            RUN_PERFORMANCE=false
            RUN_FUZZ=false
            shift
            ;;
        --integration-only)
            RUN_UNIT=false
            RUN_INTEGRATION=true
            RUN_E2E=false
            RUN_PERFORMANCE=false
            RUN_FUZZ=false
            shift
            ;;
        --e2e-only)
            RUN_UNIT=false
            RUN_INTEGRATION=false
            RUN_E2E=true
            RUN_PERFORMANCE=false
            RUN_FUZZ=false
            shift
            ;;
        --performance)
            RUN_PERFORMANCE=true
            shift
            ;;
        --fuzz)
            RUN_FUZZ=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --coverage)
            COVERAGE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --unit-only        Run only unit tests"
            echo "  --integration-only Run only integration tests"
            echo "  --e2e-only        Run only end-to-end tests"
            echo "  --performance     Include performance tests"
            echo "  --fuzz            Include fuzz tests"
            echo "  --verbose, -v     Verbose output"
            echo "  --coverage        Generate coverage report"
            echo "  --help, -h        Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Set up test environment
print_status "Setting up test environment..."

# Create test results directory
mkdir -p test-results
mkdir -p coverage

# Set environment variables for testing
export TESTING=true
export DATABASE_URL="sqlite:///:memory:"
export REDIS_URL="redis://localhost:6379/15"
export JWT_SECRET_KEY="test-secret-key"
export JWT_PUBLIC_KEY="test-public-key"
export ENCRYPTION_KEY="test-encryption-key-32-characters"
export ENCRYPTION_SALT="test-salt-16-ch"

# Build pytest arguments
PYTEST_ARGS="-v"
if [ "$VERBOSE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS -s"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_ARGS="$PYTEST_ARGS --cov=backend --cov-report=html --cov-report=term-missing"
fi

# Run unit tests
if [ "$RUN_UNIT" = true ]; then
    print_status "Running unit tests..."
    
    if [ "$COVERAGE" = true ]; then
        python -m pytest backend/tests/unit/ $PYTEST_ARGS --cov=backend --cov-report=html:coverage/backend-unit
    else
        python -m pytest backend/tests/unit/ $PYTEST_ARGS
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Unit tests passed"
    else
        print_error "Unit tests failed"
        exit 1
    fi
fi

# Run integration tests
if [ "$RUN_INTEGRATION" = true ]; then
    print_status "Running integration tests..."
    
    python -m pytest backend/tests/integration/ $PYTEST_ARGS
    
    if [ $? -eq 0 ]; then
        print_success "Integration tests passed"
    else
        print_error "Integration tests failed"
        exit 1
    fi
fi

# Run performance tests
if [ "$RUN_PERFORMANCE" = true ]; then
    print_status "Running performance tests..."
    
    python -m pytest backend/tests/performance/ $PYTEST_ARGS
    
    if [ $? -eq 0 ]; then
        print_success "Performance tests passed"
    else
        print_error "Performance tests failed"
        exit 1
    fi
fi

# Run fuzz tests
if [ "$RUN_FUZZ" = true ]; then
    print_status "Running fuzz tests..."
    
    python -m pytest backend/tests/fuzz/ $PYTEST_ARGS
    
    if [ $? -eq 0 ]; then
        print_success "Fuzz tests passed"
    else
        print_error "Fuzz tests failed"
        exit 1
    fi
fi

# Run frontend tests
if [ "$RUN_UNIT" = true ] || [ "$RUN_INTEGRATION" = true ]; then
    print_status "Running frontend tests..."
    
    cd frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        npm install
    fi
    
    # Run Jest tests
    if [ "$COVERAGE" = true ]; then
        npm test -- --coverage --coverageDirectory=../coverage/frontend
    else
        npm test
    fi
    
    if [ $? -eq 0 ]; then
        print_success "Frontend tests passed"
    else
        print_error "Frontend tests failed"
        exit 1
    fi
    
    cd ..
fi

# Run E2E tests
if [ "$RUN_E2E" = true ]; then
    print_status "Running end-to-end tests..."
    
    # Check if Playwright is installed
    if ! command_exists npx; then
        print_error "npx is required for Playwright tests"
        exit 1
    fi
    
    # Install Playwright browsers if needed
    npx playwright install
    
    # Run Playwright tests
    npx playwright test
    
    if [ $? -eq 0 ]; then
        print_success "End-to-end tests passed"
    else
        print_error "End-to-end tests failed"
        exit 1
    fi
fi

# Generate test summary
print_status "Generating test summary..."

# Count test results
if [ -f "test-results/results.json" ]; then
    TOTAL_TESTS=$(jq '.stats.total' test-results/results.json)
    PASSED_TESTS=$(jq '.stats.expected' test-results/results.json)
    FAILED_TESTS=$(jq '.stats.unexpected' test-results/results.json)
    
    echo ""
    echo "📊 Test Summary"
    echo "==============="
    echo "Total Tests: $TOTAL_TESTS"
    echo "Passed: $PASSED_TESTS"
    echo "Failed: $FAILED_TESTS"
    echo ""
    
    if [ "$FAILED_TESTS" -eq 0 ]; then
        print_success "All tests passed! 🎉"
    else
        print_error "$FAILED_TESTS tests failed"
        exit 1
    fi
else
    print_success "All tests completed successfully! 🎉"
fi

# Cleanup
print_status "Cleaning up test environment..."
unset TESTING
unset DATABASE_URL
unset REDIS_URL
unset JWT_SECRET_KEY
unset JWT_PUBLIC_KEY
unset ENCRYPTION_KEY
unset ENCRYPTION_SALT

print_success "Test run completed successfully!"

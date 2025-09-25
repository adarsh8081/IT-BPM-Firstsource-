@echo off
REM Test Runner Script for Provider Validation Application (Windows)
REM This script runs all test suites with proper configuration

setlocal enabledelayedexpansion

echo 🧪 Running Provider Validation Application Tests
echo ==================================================

REM Parse command line arguments
set RUN_UNIT=true
set RUN_INTEGRATION=true
set RUN_E2E=true
set RUN_PERFORMANCE=false
set RUN_FUZZ=false
set VERBOSE=false
set COVERAGE=false

:parse_args
if "%~1"=="" goto :args_done
if "%~1"=="--unit-only" (
    set RUN_UNIT=true
    set RUN_INTEGRATION=false
    set RUN_E2E=false
    set RUN_PERFORMANCE=false
    set RUN_FUZZ=false
    shift
    goto :parse_args
)
if "%~1"=="--integration-only" (
    set RUN_UNIT=false
    set RUN_INTEGRATION=true
    set RUN_E2E=false
    set RUN_PERFORMANCE=false
    set RUN_FUZZ=false
    shift
    goto :parse_args
)
if "%~1"=="--e2e-only" (
    set RUN_UNIT=false
    set RUN_INTEGRATION=false
    set RUN_E2E=true
    set RUN_PERFORMANCE=false
    set RUN_FUZZ=false
    shift
    goto :parse_args
)
if "%~1"=="--performance" (
    set RUN_PERFORMANCE=true
    shift
    goto :parse_args
)
if "%~1"=="--fuzz" (
    set RUN_FUZZ=true
    shift
    goto :parse_args
)
if "%~1"=="--verbose" (
    set VERBOSE=true
    shift
    goto :parse_args
)
if "%~1"=="-v" (
    set VERBOSE=true
    shift
    goto :parse_args
)
if "%~1"=="--coverage" (
    set COVERAGE=true
    shift
    goto :parse_args
)
if "%~1"=="--help" (
    echo Usage: %0 [OPTIONS]
    echo.
    echo Options:
    echo   --unit-only        Run only unit tests
    echo   --integration-only Run only integration tests
    echo   --e2e-only        Run only end-to-end tests
    echo   --performance     Include performance tests
    echo   --fuzz            Include fuzz tests
    echo   --verbose, -v     Verbose output
    echo   --coverage        Generate coverage report
    echo   --help            Show this help message
    exit /b 0
)
if "%~1"=="-h" (
    goto :--help
)
echo [ERROR] Unknown option: %~1
exit /b 1

:args_done

REM Check prerequisites
echo [INFO] Checking prerequisites...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python 3 is required but not installed
    exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js is required but not installed
    exit /b 1
)

npm --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm is required but not installed
    exit /b 1
)

echo [SUCCESS] Prerequisites check passed

REM Set up test environment
echo [INFO] Setting up test environment...

REM Create test results directory
if not exist test-results mkdir test-results
if not exist coverage mkdir coverage

REM Set environment variables for testing
set TESTING=true
set DATABASE_URL=sqlite:///:memory:
set REDIS_URL=redis://localhost:6379/15
set JWT_SECRET_KEY=test-secret-key
set JWT_PUBLIC_KEY=test-public-key
set ENCRYPTION_KEY=test-encryption-key-32-characters
set ENCRYPTION_SALT=test-salt-16-ch

REM Build pytest arguments
set PYTEST_ARGS=-v
if "%VERBOSE%"=="true" (
    set PYTEST_ARGS=%PYTEST_ARGS% -s
)

if "%COVERAGE%"=="true" (
    set PYTEST_ARGS=%PYTEST_ARGS% --cov=backend --cov-report=html --cov-report=term-missing
)

REM Run unit tests
if "%RUN_UNIT%"=="true" (
    echo [INFO] Running unit tests...
    
    if "%COVERAGE%"=="true" (
        python -m pytest backend/tests/unit/ %PYTEST_ARGS% --cov=backend --cov-report=html:coverage/backend-unit
    ) else (
        python -m pytest backend/tests/unit/ %PYTEST_ARGS%
    )
    
    if errorlevel 1 (
        echo [ERROR] Unit tests failed
        exit /b 1
    )
    echo [SUCCESS] Unit tests passed
)

REM Run integration tests
if "%RUN_INTEGRATION%"=="true" (
    echo [INFO] Running integration tests...
    
    python -m pytest backend/tests/integration/ %PYTEST_ARGS%
    
    if errorlevel 1 (
        echo [ERROR] Integration tests failed
        exit /b 1
    )
    echo [SUCCESS] Integration tests passed
)

REM Run performance tests
if "%RUN_PERFORMANCE%"=="true" (
    echo [INFO] Running performance tests...
    
    python -m pytest backend/tests/performance/ %PYTEST_ARGS%
    
    if errorlevel 1 (
        echo [ERROR] Performance tests failed
        exit /b 1
    )
    echo [SUCCESS] Performance tests passed
)

REM Run fuzz tests
if "%RUN_FUZZ%"=="true" (
    echo [INFO] Running fuzz tests...
    
    python -m pytest backend/tests/fuzz/ %PYTEST_ARGS%
    
    if errorlevel 1 (
        echo [ERROR] Fuzz tests failed
        exit /b 1
    )
    echo [SUCCESS] Fuzz tests passed
)

REM Run frontend tests
if "%RUN_UNIT%"=="true" (
    echo [INFO] Running frontend tests...
    
    cd frontend
    
    REM Install dependencies if needed
    if not exist node_modules (
        echo [INFO] Installing frontend dependencies...
        npm install
    )
    
    REM Run Jest tests
    if "%COVERAGE%"=="true" (
        npm test -- --coverage --coverageDirectory=../coverage/frontend
    ) else (
        npm test
    )
    
    if errorlevel 1 (
        echo [ERROR] Frontend tests failed
        exit /b 1
    )
    echo [SUCCESS] Frontend tests passed
    
    cd ..
)

REM Run E2E tests
if "%RUN_E2E%"=="true" (
    echo [INFO] Running end-to-end tests...
    
    REM Check if npx is available
    npx --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] npx is required for Playwright tests
        exit /b 1
    )
    
    REM Install Playwright browsers if needed
    npx playwright install
    
    REM Run Playwright tests
    npx playwright test
    
    if errorlevel 1 (
        echo [ERROR] End-to-end tests failed
        exit /b 1
    )
    echo [SUCCESS] End-to-end tests passed
)

REM Cleanup
echo [INFO] Cleaning up test environment...
set TESTING=
set DATABASE_URL=
set REDIS_URL=
set JWT_SECRET_KEY=
set JWT_PUBLIC_KEY=
set ENCRYPTION_KEY=
set ENCRYPTION_SALT=

echo [SUCCESS] Test run completed successfully!
echo.
echo 📊 All tests passed! 🎉

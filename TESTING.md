# Testing Documentation

This document provides comprehensive information about the testing strategy, test suites, and how to run tests for the Provider Data Validation & Directory Management application.

## Testing Strategy

Our testing strategy follows a multi-layered approach to ensure comprehensive coverage and reliability:

### 1. **Unit Tests** 🔧
- **Purpose**: Test individual components in isolation
- **Scope**: Functions, classes, and modules
- **Tools**: pytest, Jest
- **Coverage Target**: 80%+

### 2. **Integration Tests** 🔗
- **Purpose**: Test component interactions and data flow
- **Scope**: API endpoints, database operations, external service integrations
- **Tools**: pytest with mock external services
- **Coverage Target**: Critical user paths

### 3. **End-to-End Tests** 🎭
- **Purpose**: Test complete user workflows
- **Scope**: Full application flows from UI to database
- **Tools**: Playwright
- **Coverage Target**: Main user journeys

### 4. **Performance Tests** ⚡
- **Purpose**: Ensure system meets performance requirements
- **Scope**: Validation throughput, response times, scalability
- **Tools**: pytest with timing assertions
- **Target**: 100 providers in <5 minutes

### 5. **Fuzz Tests** 🎯
- **Purpose**: Test robustness against malformed inputs
- **Scope**: OCR pipeline, PDF processing, API inputs
- **Tools**: pytest with generated test data
- **Coverage Target**: Edge cases and error conditions

## Test Structure

```
backend/tests/
├── unit/                    # Unit tests
│   ├── test_connectors.py   # Connector unit tests
│   ├── test_orchestrator.py # Orchestrator unit tests
│   └── conftest.py         # Shared fixtures
├── integration/             # Integration tests
│   └── test_validation_integration.py
├── performance/             # Performance tests
│   └── test_validation_performance.py
└── fuzz/                   # Fuzz tests
    └── test_ocr_fuzz.py

frontend/tests/
├── components/              # Component tests
│   ├── ConfidenceBadge.test.tsx
│   ├── SourceChip.test.tsx
│   └── __snapshots__/      # Jest snapshots
├── e2e/                    # End-to-end tests
│   └── validation-flows.spec.ts
├── jest.config.js          # Jest configuration
└── jest.setup.js          # Jest setup

scripts/
├── run_tests.sh           # Unix test runner
└── run_tests.bat          # Windows test runner
```

## Running Tests

### Quick Start

```bash
# Run all tests
./scripts/run_tests.sh

# Windows
scripts\run_tests.bat
```

### Specific Test Suites

```bash
# Unit tests only
./scripts/run_tests.sh --unit-only

# Integration tests only
./scripts/run_tests.sh --integration-only

# End-to-end tests only
./scripts/run_tests.sh --e2e-only

# Performance tests
./scripts/run_tests.sh --performance

# Fuzz tests
./scripts/run_tests.sh --fuzz
```

### Advanced Options

```bash
# With coverage report
./scripts/run_tests.sh --coverage

# Verbose output
./scripts/run_tests.sh --verbose

# Combined options
./scripts/run_tests.sh --unit-only --coverage --verbose
```

### Manual Test Execution

#### Backend Tests (pytest)

```bash
# All backend tests
python -m pytest backend/tests/

# Specific test file
python -m pytest backend/tests/unit/test_connectors.py

# Specific test function
python -m pytest backend/tests/unit/test_connectors.py::TestNPIConnector::test_fetch_provider_by_npi_success

# With coverage
python -m pytest --cov=backend backend/tests/

# Performance tests only
python -m pytest backend/tests/performance/ -v
```

#### Frontend Tests (Jest)

```bash
cd frontend

# All frontend tests
npm test

# Watch mode
npm test -- --watch

# With coverage
npm test -- --coverage

# Specific test file
npm test ConfidenceBadge.test.tsx
```

#### End-to-End Tests (Playwright)

```bash
# Install browsers (first time only)
npx playwright install

# Run all E2E tests
npx playwright test

# Run specific test file
npx playwright test validation-flows.spec.ts

# Run in headed mode (see browser)
npx playwright test --headed

# Run on specific browser
npx playwright test --project=chromium
```

## Test Categories

### Unit Tests

#### Connector Tests (`test_connectors.py`)
- **NPI Connector**: API responses, error handling, rate limiting
- **Google Places Connector**: Geocoding, place details, address validation
- **State Board Connector**: License verification, robots.txt compliance
- **Validation Rules**: Phone, email, address, license validation logic

#### Orchestrator Tests (`test_orchestrator.py`)
- **Validation Orchestrator**: Worker coordination, confidence aggregation
- **Report Generator**: Report creation, field analysis, recommendations
- **Rate Limiter**: Redis-based rate limiting, backoff strategies
- **Idempotency Manager**: Request deduplication, cached responses

### Integration Tests

#### Full Validation Pipeline (`test_validation_integration.py`)
- **5 Test Providers**: Known outcomes for validation testing
  - Valid provider (high confidence)
  - Warning provider (email issues)
  - Invalid provider (multiple issues)
  - Suspended license provider
  - Partial match provider
- **Database Writes**: Verify validation results are saved
- **Confidence Thresholds**: Assert expected confidence ranges
- **Audit Logging**: Verify audit trail creation

### Performance Tests

#### Validation Throughput (`test_validation_performance.py`)
- **100 Provider Validation**: Target <5 minutes
- **Parallel Processing**: Concurrent validation workers
- **Memory Usage**: Monitor memory consumption
- **Scalability**: Test different concurrency levels
- **Database Performance**: Write performance testing

### Fuzz Tests

#### OCR Pipeline Robustness (`test_ocr_fuzz.py`)
- **Malformed Images**: Corrupted, empty, edge case images
- **Random Text**: Generated text with various patterns
- **Memory Limits**: Large image processing
- **Concurrent Processing**: Parallel OCR operations
- **PDF Processing**: Malformed PDF handling

### End-to-End Tests

#### User Workflows (`validation-flows.spec.ts`)
- **CSV Import**: Upload and validate provider data
- **Batch Validation**: Run validation jobs
- **Provider Review**: Accept/reject providers
- **Manual Review Queue**: Reviewer assignment and notes
- **Export Reports**: CSV and PDF export
- **Dashboard KPIs**: Performance metrics display
- **Bulk Actions**: Multi-provider operations
- **Search and Filter**: Provider discovery
- **Mobile Responsiveness**: Touch interactions

## Test Data

### Mock External APIs

All tests use mocked external API responses to ensure:
- **Reliability**: Tests don't depend on external services
- **Speed**: No network delays in test execution
- **Consistency**: Predictable test outcomes
- **Cost**: No API usage charges during testing

### Sample Data Sets

#### Integration Test Providers
```json
{
  "PROV_VALID_001": {
    "expected_confidence": 0.85,
    "expected_status": "valid",
    "expected_flags": []
  },
  "PROV_WARNING_001": {
    "expected_confidence": 0.65,
    "expected_status": "warning",
    "expected_flags": ["LOW_CONFIDENCE_EMAIL"]
  },
  "PROV_INVALID_001": {
    "expected_confidence": 0.2,
    "expected_status": "invalid",
    "expected_flags": ["INVALID_NPI", "INVALID_ADDRESS", "INVALID_LICENSE"]
  }
}
```

#### Performance Test Data
- **100 Providers**: Generated with realistic data patterns
- **Varied Complexity**: Different validation scenarios
- **Known Outcomes**: Predictable results for assertions

## Test Configuration

### Environment Variables

```bash
# Test environment
TESTING=true
DATABASE_URL=sqlite:///:memory:
REDIS_URL=redis://localhost:6379/15
JWT_SECRET_KEY=test-secret-key
JWT_PUBLIC_KEY=test-public-key
ENCRYPTION_KEY=test-encryption-key-32-characters
ENCRYPTION_SALT=test-salt-16-ch
```

### Pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = backend/tests
addopts = -v --tb=short --strict-markers
markers =
    unit: Unit tests
    integration: Integration tests
    performance: Performance tests
    fuzz: Fuzz tests
    slow: Slow running tests
```

### Jest Configuration (`frontend/tests/jest.config.js`)

```javascript
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/tests/jest.setup.js'],
  collectCoverageFrom: ['components/**/*.{js,jsx,ts,tsx}'],
  coverageThreshold: {
    global: { branches: 80, functions: 80, lines: 80, statements: 80 }
  }
}
```

### Playwright Configuration (`playwright.config.ts`)

```typescript
export default defineConfig({
  testDir: './frontend/tests/e2e',
  use: { baseURL: 'http://localhost:3000' },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } }
  ]
})
```

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
      - uses: actions/setup-node@v3
      - run: ./scripts/run_tests.sh --coverage
```

### Test Reports

- **Coverage Reports**: HTML coverage reports in `coverage/` directory
- **Test Results**: JSON and JUnit reports in `test-results/`
- **Playwright Reports**: HTML reports with screenshots and videos
- **Performance Metrics**: Timing and throughput measurements

## Best Practices

### Writing Tests

1. **Arrange-Act-Assert**: Structure tests clearly
2. **Descriptive Names**: Use clear, descriptive test names
3. **Single Responsibility**: One assertion per test
4. **Mock External Dependencies**: Use mocks for external services
5. **Test Edge Cases**: Include boundary conditions and error cases

### Test Maintenance

1. **Keep Tests Fast**: Optimize for speed
2. **Independent Tests**: Tests should not depend on each other
3. **Clean Setup/Teardown**: Proper test isolation
4. **Regular Updates**: Update tests when code changes
5. **Monitor Coverage**: Track test coverage metrics

### Debugging Tests

```bash
# Debug specific test
python -m pytest backend/tests/unit/test_connectors.py::TestNPIConnector::test_fetch_provider_by_npi_success -v -s

# Debug with breakpoint
python -m pytest --pdb backend/tests/unit/test_connectors.py

# Show test output
python -m pytest -s backend/tests/unit/test_connectors.py

# Run only failed tests
python -m pytest --lf
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure Python path includes project root
2. **Database Issues**: Use in-memory SQLite for tests
3. **Redis Connection**: Mock Redis for unit tests
4. **Port Conflicts**: Use different ports for test servers
5. **File Permissions**: Ensure test scripts are executable

### Performance Issues

1. **Slow Tests**: Use `--durations` to identify slow tests
2. **Memory Leaks**: Monitor memory usage in performance tests
3. **Concurrent Tests**: Use appropriate worker counts
4. **Database Cleanup**: Ensure proper test isolation

### Coverage Issues

1. **Low Coverage**: Add tests for untested code paths
2. **Coverage Gaps**: Review coverage reports for missing areas
3. **Threshold Failures**: Adjust coverage thresholds if needed
4. **Excluded Files**: Update coverage configuration

## Metrics and Monitoring

### Test Metrics

- **Test Count**: ~500+ tests across all suites
- **Coverage**: 80%+ code coverage target
- **Execution Time**: <10 minutes for full test suite
- **Success Rate**: 99%+ test success rate
- **Performance**: 100 providers validated in <5 minutes

### Quality Gates

- All tests must pass before deployment
- Coverage must meet minimum thresholds
- Performance tests must meet timing requirements
- No critical security vulnerabilities in dependencies

## Conclusion

This comprehensive testing strategy ensures the Provider Data Validation application is reliable, performant, and maintainable. The multi-layered approach provides confidence in both individual components and complete user workflows, while performance and fuzz testing ensure robustness under various conditions.

For questions or issues with testing, please refer to the troubleshooting section or contact the development team.

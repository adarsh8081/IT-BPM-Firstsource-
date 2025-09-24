# Backend - Provider Validation API

FastAPI backend application for the Provider Data Validation & Directory Management System.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -e .

# Start development server
uvicorn main:app --reload

# Run tests
pytest

# Run linting
black . && isort . && flake8 .
```

## 📁 Structure

```
backend/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── database.py            # Database setup and sessions
├── models.py              # SQLAlchemy models
├── schemas.py             # Pydantic schemas
├── routers/               # API route handlers
│   ├── health.py          # Health check endpoints
│   ├── providers.py       # Provider management
│   ├── validation.py      # Validation endpoints
│   └── dashboard.py       # Dashboard analytics
├── services/              # Business logic
│   ├── provider_service.py
│   └── validation_service.py
├── connectors/            # External API connectors
│   ├── base.py            # Base connector class
│   ├── npi_connector.py   # NPI Registry API
│   ├── google_places_connector.py # Google Places API
│   └── state_board_connector.py   # State Medical Board API
├── workers/               # Background job workers
│   ├── validation_worker.py
│   └── queue_manager.py
├── middleware/            # Custom middleware
│   ├── logging_middleware.py
│   └── security_middleware.py
├── scripts/               # Utility scripts
│   ├── generate_demo_data.py
│   ├── generate_pdf_documents.py
│   ├── migrate_database.py
│   └── run_worker.py
└── alembic/               # Database migrations
    ├── env.py
    ├── script.py.mako
    └── versions/
```

## 🛠️ Available Scripts

### Development
- `uvicorn main:app --reload` - Start development server
- `python -m workers.validation_worker` - Start validation worker

### Testing
- `pytest` - Run all tests
- `pytest --cov=backend` - Run tests with coverage
- `pytest tests/test_providers.py` - Run specific test file

### Code Quality
- `black .` - Format code with Black
- `isort .` - Sort imports with isort
- `flake8 .` - Lint code with flake8
- `mypy .` - Type check with mypy

### Database
- `alembic upgrade head` - Run database migrations
- `alembic revision --autogenerate -m "message"` - Create new migration

## 🔧 Configuration

### Environment Variables

Create `.env`:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/provider_validation
REDIS_URL=redis://localhost:6379/0
NPI_API_KEY=your-npi-api-key
GOOGLE_PLACES_API_KEY=your-google-places-api-key
GOOGLE_MAPS_API_KEY=your-google-maps-api-key
SECRET_KEY=your-secret-key
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## 🗄️ Database

### Models

- **Provider**: Provider profile information
- **ValidationJob**: Background validation jobs
- **ValidationResult**: Validation results and scores

### Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Run migrations
alembic upgrade head

# Downgrade
alembic downgrade -1
```

## 🔌 API Endpoints

### Health & Status
- `GET /api/health/` - Health check
- `GET /api/status` - API status

### Providers
- `POST /api/providers/` - Create provider
- `GET /api/providers/` - List providers
- `GET /api/providers/{id}` - Get provider
- `PUT /api/providers/{id}` - Update provider
- `DELETE /api/providers/{id}` - Delete provider

### Validation
- `POST /api/validation/jobs` - Create validation job
- `GET /api/validation/jobs` - List validation jobs
- `GET /api/validation/results/{provider_id}` - Get validation results

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics
- `GET /api/dashboard/analytics/validation-performance` - Performance metrics

## 🔄 Job Queue

### Validation Worker

```bash
# Start validation worker
python -m workers.validation_worker
```

### Queue Management

The system uses Redis with RQ for background job processing:
- Automatic retry for failed jobs
- Priority-based job scheduling
- Real-time progress monitoring

## 🔌 External Integrations

### NPI Registry API
- Real-time provider validation
- Rate limiting and error handling
- PII redaction in logs

### Google Places API
- Address validation and geocoding
- Place details and suggestions
- Rate limiting compliance

### State Medical Board APIs
- License validation (mock implementation)
- Disciplinary action lookup
- State-specific validation rules

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_providers.py

# Run with verbose output
pytest -v
```

## 📊 Monitoring

### Health Checks
- Database connectivity
- Redis connectivity
- External API status
- Worker status

### Logging
- Structured JSON logging
- Request/response logging
- Error tracking
- Performance metrics

## 🚀 Deployment

### Docker

```bash
# Build image
docker build -t provider-validation-backend .

# Run container
docker run -p 8000:8000 provider-validation-backend
```

### Production

```bash
# Install production dependencies
pip install -e .[dev]

# Run with gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
```

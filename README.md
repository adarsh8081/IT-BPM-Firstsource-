# Provider Data Validation & Directory Management System
## Mono-repo Structure

[![CI/CD Pipeline](https://github.com/adarsh8081/IT-BPM-Firstsource-/actions/workflows/ci.yml/badge.svg)](https://github.com/adarsh8081/IT-BPM-Firstsource-/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This is a mono-repo containing a full-stack healthcare provider data validation and directory management system.

## 📁 Repository Structure

```
provider-validation-monorepo/
├── frontend/                 # Next.js + TypeScript + Tailwind CSS
│   ├── app/                 # Next.js App Router
│   ├── components/          # React components
│   ├── lib/                 # Utilities and helpers
│   ├── hooks/               # Custom React hooks
│   ├── types/               # TypeScript type definitions
│   ├── utils/               # Utility functions
│   ├── package.json         # Frontend dependencies
│   ├── Dockerfile           # Frontend container
│   └── README.md            # Frontend documentation
├── backend/                 # FastAPI + Python
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routers/             # API route handlers
│   ├── services/            # Business logic
│   ├── connectors/          # External API connectors
│   ├── workers/             # Background job workers
│   ├── middleware/          # Custom middleware
│   ├── scripts/             # Utility scripts
│   ├── alembic/             # Database migrations
│   ├── pyproject.toml       # Python dependencies
│   ├── Dockerfile           # Backend container
│   └── README.md            # Backend documentation
├── tests/                   # Integration tests
├── docker-compose.dev.yml   # Development environment
├── package.json             # Mono-repo scripts
└── README.md                # This file
```

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.11+
- Docker & Docker Compose

### Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/adarsh8081/IT-BPM-Firstsource-.git
   cd IT-BPM-Firstsource-
   ```

2. **Start all services with Docker Compose**
   ```bash
   npm run dev
   # or
   docker-compose -f docker-compose.dev.yml up --build
   ```

3. **Access the applications**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Database**: localhost:5432
   - **Redis**: localhost:6379

4. **Run database migrations**
   ```bash
   npm run migrate
   ```

5. **Generate demo data**
   ```bash
   npm run demo-data
   ```

### Individual Service Development

#### Frontend Development
```bash
# Install dependencies
cd frontend && npm install

# Start development server
npm run frontend:dev

# Run tests
npm run frontend:test

# Build for production
npm run frontend:build
```

#### Backend Development
```bash
# Install dependencies
cd backend && pip install -e .

# Start development server
npm run backend:dev

# Run tests
npm run backend:test

# Run linting
npm run backend:lint
```

## 🛠️ Available Scripts

### Mono-repo Scripts
- `npm run dev` - Start all services in development mode
- `npm run dev:build` - Build and start all services
- `npm run dev:down` - Stop all services
- `npm run dev:logs` - View logs from all services
- `npm run test` - Run tests for both frontend and backend
- `npm run lint` - Run linting for both frontend and backend
- `npm run clean` - Clean up Docker containers and volumes
- `npm run setup` - Install dependencies for all services
- `npm run migrate` - Run database migrations
- `npm run demo-data` - Generate demo data

### Frontend Scripts
- `npm run frontend:dev` - Start Next.js development server
- `npm run frontend:build` - Build Next.js application
- `npm run frontend:test` - Run frontend tests

### Backend Scripts
- `npm run backend:dev` - Start FastAPI development server
- `npm run backend:test` - Run backend tests
- `npm run backend:lint` - Run Python linting

## 🏗️ Architecture

### Frontend (`/frontend`)
- **Framework**: Next.js 14 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **UI Components**: Headless UI, Heroicons
- **Testing**: Jest, React Testing Library

### Backend (`/backend`)
- **Framework**: FastAPI
- **Language**: Python 3.11
- **Database**: PostgreSQL with SQLAlchemy
- **Job Queue**: Redis with RQ
- **Testing**: pytest
- **Documentation**: Auto-generated with FastAPI

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Development**: Hot reload for both frontend and backend
- **Database**: PostgreSQL with health checks
- **Cache**: Redis for job queue and caching

## 📊 Services

### Core Services
- **Frontend**: Next.js application on port 3000
- **Backend**: FastAPI application on port 8000
- **PostgreSQL**: Database on port 5432
- **Redis**: Cache and job queue on port 6379
- **Worker**: Background job processor

### External Integrations
- **NPI Registry API**: Provider validation
- **Google Places API**: Address validation
- **State Medical Board APIs**: License validation

## 🔧 Development Workflow

1. **Start Development Environment**
   ```bash
   npm run dev
   ```

2. **Make Changes**
   - Frontend changes auto-reload on port 3000
   - Backend changes auto-reload on port 8000

3. **Run Tests**
   ```bash
   npm run test
   ```

4. **Check Code Quality**
   ```bash
   npm run lint
   ```

5. **View Logs**
   ```bash
   npm run dev:logs
   ```

## 📝 Environment Variables

### Frontend (.env.local)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Backend (.env)
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/provider_validation
REDIS_URL=redis://localhost:6379/0
NPI_API_KEY=your-npi-api-key
GOOGLE_PLACES_API_KEY=your-google-places-api-key
SECRET_KEY=your-secret-key
DEBUG=true
ENVIRONMENT=development
```

## 🧪 Testing

### Frontend Tests
```bash
cd frontend
npm test
npm run test:coverage
```

### Backend Tests
```bash
cd backend
pytest
pytest --cov=backend --cov-report=html
```

### Integration Tests
```bash
# Start test environment
docker-compose -f docker-compose.dev.yml up -d

# Run integration tests
pytest tests/
```

## 🚀 Deployment

### Production Build
```bash
# Build frontend
cd frontend && npm run build

# Build backend
cd backend && pip install -e .

# Build Docker images
docker-compose -f docker-compose.prod.yml build
```

### Docker Production
```bash
# Start production environment
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Documentation

- **Frontend Documentation**: [frontend/README.md](frontend/README.md)
- **Backend Documentation**: [backend/README.md](backend/README.md)
- **API Documentation**: http://localhost:8000/docs (when running)
- **Architecture Overview**: [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)
- **Presentation**: [PRESENTATION.md](PRESENTATION.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`npm run test`)
5. Run linting (`npm run lint`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📞 Support

- **Repository**: [https://github.com/adarsh8081/IT-BPM-Firstsource-](https://github.com/adarsh8081/IT-BPM-Firstsource-.git)
- **Issues**: GitHub Issues for bug reports and feature requests
- **Documentation**: Comprehensive setup and API documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for Healthcare Payers**  
*Delivering accurate, compliant, and efficient provider data management*

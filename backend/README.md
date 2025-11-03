# mamaope_legal AI CDSS

A professional FastAPI-based Clinical Decision Support System with AI-powered diagnosis capabilities.

## Project Structure

```
backend/
├── src/
│   └── mamaope_legal/           # Main application package
│       ├── __init__.py
│       ├── main.py           # FastAPI application entry point
│       ├── api/              # API endpoints
│       │   ├── __init__.py
│       │   └── v1/           # API version 1
│       │       ├── __init__.py
│       │       ├── auth.py   # Authentication endpoints
│       │       └── diagnosis.py # Diagnosis endpoints
│       ├── core/              # Core application components
│       │   ├── __init__.py
│       │   ├── config.py     # Configuration management
│       │   ├── database.py   # Database connection
│       │   └── security.py   # Security utilities
│       ├── models/            # Database models
│       │   ├── __init__.py
│       │   ├── base.py       # Base model
│       │   └── user.py       # User model
│       ├── schemas/           # Pydantic schemas
│       │   └── __init__.py   # Request/response schemas
│       └── services/          # Business logic services
│           ├── __init__.py
│           ├── conversational_service.py # AI service
│           ├── database_service.py      # Database service
│           └── vectorstore_manager.py   # Vector store service
├── alembic/                   # Database migrations
├── scripts/                   # Utility scripts
├── tests/                     # Test files
├── Dockerfile                 # Docker configuration
├── pyproject.toml            # Python project configuration
└── requirements.txt          # Python dependencies
```

## Features

- **AI-Powered Diagnosis**: Integration with Google Vertex AI Gemini 2.5 Flash
- **User Authentication**: JWT-based authentication with role-based access control
- **Database Management**: PostgreSQL with Alembic migrations
- **Security**: HIPAA/GDPR compliant security measures
- **API Documentation**: Automatic OpenAPI/Swagger documentation
- **Docker Support**: Containerized deployment

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker and Docker Compose
- Google Cloud credentials for Vertex AI

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd mamaope_legal_model_v1
```

2. Set up environment variables:
```bash
cp env.example .env
# Edit .env with your configuration
```

3. Start with Docker Compose:
```bash
docker compose up --build
```

### API Endpoints

- **Authentication**: `/api/v1/auth/`
  - `POST /register` - User registration
  - `POST /login` - User login
  - `GET /users` - List users (admin only)

- **Diagnosis**: `/api/v1/diagnosis/`
  - `POST /diagnose` - AI diagnosis (requires authentication)
  - `GET /health` - Service health check

- **Health Check**: `/api/v1/health` - Application health status

## Development

### Local Development Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -e .
pip install -e ".[dev]"
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start development server:
```bash
uvicorn mamaope_legal.main:app --reload
```

### Testing

```bash
pytest
```

### Code Quality

```bash
black src/
isort src/
flake8 src/
mypy src/
```

## Configuration

The application uses environment variables for configuration. See `env.example` for required variables.

### Required Environment Variables

- `SECRET_KEY`: JWT secret key (min 32 characters)
- `ENCRYPTION_KEY`: Data encryption key (min 32 characters)
- `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`: Database configuration
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to Google Cloud credentials JSON
- `GOOGLE_CLOUD_PROJECT`: Google Cloud project ID
- `GOOGLE_CLOUD_LOCATION`: Google Cloud location

## Security

This application implements medical software security standards:

- **Data Encryption**: All PHI data is encrypted at rest and in transit
- **Authentication**: JWT-based authentication with secure password requirements
- **Authorization**: Role-based access control (user, admin, super_admin)
- **Input Validation**: Comprehensive input sanitization and validation
- **Audit Logging**: Secure logging with PHI redaction
- **Rate Limiting**: Protection against brute force attacks

## License

MIT License - see LICENSE file for details.

## Support

For support and questions, contact: support@mamaope_legal.ai

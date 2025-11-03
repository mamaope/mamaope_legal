# Mamaope Legal AI - Enhanced Security Edition

## ⚖️ Legal AI Consultation System

**Mamaope Legal AI** is a secure, GDPR-compliant AI-powered Legal Consultation System that uses Retrieval-Augmented Generation (RAG) to assist legal professionals with case analysis and legal decision-making.

## 📚 Documentation

- **[Complete API Documentation](API_DOCUMENTATION.md)** - Comprehensive API reference with examples

## 🔒 Security Features

### **Medical Software Security Standards**
- **GDPR Compliance**: Data protection and privacy controls
- **SOC 2 Type II**: Security, availability, and confidentiality controls

### **Authentication & Authorization**
- **JWT-based Authentication**: Secure token-based authentication
- **Password Security**: Bcrypt hashing with salt, strong password requirements
- **Rate Limiting**: Protection against brute force attacks
- **Session Management**: Secure session handling with refresh tokens
- **Account Lockout**: Automatic account locking after failed attempts

### **Data Protection**
- **PHI Encryption**: AES-256 encryption for sensitive medical data
- **Secure Logging**: PHI sanitization in logs
- **Input Validation**: Comprehensive input sanitization and validation
- **Audit Trails**: Complete audit logging for compliance
- **Data Retention**: Configurable data retention policies

### **API Security**
- **CORS Protection**: Configurable Cross-Origin Resource Sharing
- **Request Validation**: Pydantic-based input validation
- **Error Handling**: Secure error messages without information leakage
- **Rate Limiting**: API endpoint rate limiting
- **Security Headers**: Comprehensive security headers

## 🚀 Quick Start

### **Prerequisites**
- Python 3.11+
- PostgreSQL 15+
- Docker & Docker Compose
- Google Cloud Platform account
- Azure OpenAI account
- Zilliz Cloud account

### **Installation**

1. **Clone the repository**
```bash
git clone https://github.com/mamaope/mamaope_legal.git
cd mamaope_legal
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your configuration
```

### **Google Cloud Setup (Required for AI Features)**

**⚠️ Important**: The AI features (legal analysis, chat) require Google Cloud Vertex AI to be properly configured. Without valid credentials, the application will return "AI service is currently unavailable" errors.

1. **Create a Google Cloud Project**
   ```bash
   # Go to Google Cloud Console and create a new project
   # Enable Vertex AI API for your project
   ```

2. **Create a Service Account**
   ```bash
   # In Google Cloud Console, go to IAM & Admin > Service Accounts
   # Create a new service account with Vertex AI permissions
   # Download the JSON key file
   ```

3. **Set Environment Variables**
   ```bash
   export GOOGLE_CLOUD_PROJECT=your-project-id
   export GOOGLE_CLOUD_LOCATION=us-central1
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account.json
   ```

4. **For Docker Deployment**
   ```bash
   # Place your service account JSON file in the backend directory
   # The docker-compose.yml will mount it automatically
   ```

### **Required Environment Variables**

```bash
# Security
SECRET_KEY=your-super-secure-secret-key-min-32-chars
ENCRYPTION_KEY=your-encryption-key-min-32-chars

# Database
DB_USER=mamaope_legal
DB_PASSWORD=your-secure-db-password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mamaope_legal_ai

# Google Cloud / Vertex AI
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-openai-key
API_VERSION=2024-02-01
DEPLOYMENT=text-embedding-3-large

# Zilliz/Milvus
MILVUS_URI=https://your-cluster.zillizcloud.com
MILVUS_TOKEN=your-milvus-token
MILVUS_COLLECTION_NAME=medical_knowledge

# AWS S3
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_REGION=us-east-1
AWS_S3_BUCKET=mamaope_legal-cdss

# Application
ENV=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=["https://your-frontend-domain.com"]
```

### **Database Setup**

1. **Create database**
```bash
createdb mamaope_legal_cdss
```

2. **Run migrations**
```bash
alembic upgrade head
```

### **Docker Deployment**

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Stop services
docker-compose down
```
Notes:
- **Data**: Large binaries live under `backend/data/` and are gitignored.
- **Secrets**: Service account JSON files must not be committed; use env vars or mounted secrets.
- **API root**: Backend serves under `/api/v1` (see `ApplicationConfig.api_root_path`).

## 🏗️ Architecture

### **System Architecture**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   FastAPI       │    │   PostgreSQL    │
│   (React/Vue)   │◄──►│   Backend       │◄──►│   Database      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Vector Store  │
                       │   (Zilliz)      │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   AI Models     │
                       │   (Vertex AI)   │
                       └─────────────────┘
```

### **Security Layers**
1. **Network Security**: HTTPS, CORS, Security Headers
2. **Application Security**: Authentication, Authorization, Input Validation
3. **Data Security**: Encryption, Audit Logging, PHI Protection
4. **Infrastructure Security**: Container Security, Secrets Management

## 📚 API Documentation

### **Authentication Endpoints**

#### **Register User**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "mary",
  "email": "mary@leagl.com",
  "password": "SecurePassword123!",
  "full_name": "Mary Hellen"
}
```

#### **Login**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "mary",
  "password": "SecurePassword123!"
}
```

#### **Refresh Token**
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "your-refresh-token"
}
```

### **System Endpoints**

#### **Health Check**
```http
GET /api/v1/health
```

## 🧪 Testing

### **Run Tests**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run security tests
pytest -m security

# Run integration tests
pytest -m integration
```

### **Test Coverage**
- **Unit Tests**: >90% coverage
- **Integration Tests**: Critical user flows
- **Security Tests**: Authentication, authorization, data protection
- **Performance Tests**: Load testing, stress testing

## 🔧 Development

### **Code Quality**
```bash
# Format code
black backend/src/mamaope_legal
isort backend/src/mamaope_legal

# Lint code
flake8 backend/src/mamaope_legal
mypy backend/src/mamaope_legal

# Security scan
bandit -r backend/src/mamaope_legal
safety check
```

### **Pre-commit Hooks**
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

## 📊 Monitoring & Logging

### **Logging**
- **Structured Logging**: JSON-formatted logs
- **PHI Sanitization**: Automatic PHI removal from logs
- **Audit Logging**: Complete audit trail
- **Security Events**: Security event tracking

### **Monitoring**
- **Health Checks**: Comprehensive health monitoring
- **Performance Metrics**: Response times, throughput
- **Security Metrics**: Failed logins, suspicious activity
- **Error Tracking**: Error rates and patterns

## 🚨 Security Considerations

### **Production Deployment**
1. **Use HTTPS**: Always use HTTPS in production
2. **Secure Secrets**: Use proper secrets management
3. **Network Security**: Configure firewalls and VPCs
4. **Regular Updates**: Keep dependencies updated
5. **Security Scanning**: Regular security scans

### **Compliance**
- **GDPR**: Data protection and privacy controls
- **SOC 2**: Security and availability controls
- **ISO 13485**: Quality management system

### **Incident Response**
1. **Security Incident Plan**: Documented response procedures
2. **Audit Logs**: Complete audit trail for investigations
4. **Recovery Procedures**: Data backup and recovery

## 🤝 Contributing

### **Security Guidelines**
1. **Security Review**: All code changes require security review
2. **Vulnerability Reporting**: Report security issues responsibly
3. **Code Standards**: Follow security coding standards
4. **Testing**: Comprehensive security testing required

### **Development Process**
1. **Fork Repository**: Create feature branch
2. **Security Scan**: Run security scans
3. **Code Review**: Security-focused code review
4. **Testing**: Comprehensive testing
5. **Documentation**: Update security documentation

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### **Security Issues**
- **Email**: security@mamaope_legal.com
- **PGP Key**: Available on request
- **Response Time**: 24 hours for critical issues

### **General Support**
- **Documentation**: [legal.mamaope.com](https://legal.mamaope.com/docs)
- **Issues**: GitHub Issues

## 🔗 Links

- **Security Policy**: [SECURITY.md](SECURITY.md)
- **Changelog**: [CHANGELOG.md](CHANGELOG.md)

---

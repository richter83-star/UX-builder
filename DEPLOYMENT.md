# Deployment Guide for Kalshi Probability Analysis Agent

This guide provides multiple deployment options for the Kalshi Probability Analysis Agent.

## 🚀 Quick Start (Local Development)

### Prerequisites
- Python 3.9+
- Node.js 18+
- PostgreSQL 12+
- Redis 6+

### Option 1: Direct Local Deployment

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your Kalshi API credentials

# Install PostgreSQL and Redis, then update DATABASE_URL and REDIS_URL in .env
```

#### 2. Database Setup
```bash
# Create PostgreSQL database
createdb kalshi_agent

# (Optional) Run database migrations if using Alembic
# alembic upgrade head
```

#### 3. Frontend Setup
```bash
# Navigate to frontend directory
cd ../frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your API URLs
```

#### 4. Start Services
```bash
# Start backend (in terminal 1)
cd ../backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend (in terminal 2)
cd ../frontend
npm start

# Start Redis (in terminal 3)
redis-server

# PostgreSQL should be running as a service
```

#### 5. Access the Application
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Option 2: Docker Compose (Recommended for Production)

#### Prerequisites
- Docker
- Docker Compose

#### 1. Environment Setup
```bash
# Clone the repository
git clone <repository-url>
cd UX-builder

# Copy environment templates
cp backend/.env.example .env
cp frontend/.env.example frontend/.env

# Edit .env files with your configuration
nano .env
```

#### 2. Required Environment Variables
```bash
# Core Configuration
SECRET_KEY=your_super_secret_key_change_in_production
KALSHI_API_KEY=your_kalshi_api_key
KALSHI_PRIVATE_KEY=your_kalshi_private_key
KALSHI_ENVIRONMENT=sandbox

# Database
DATABASE_URL=postgresql://kalshi_user:kalshi_password@postgres:5432/kalshi_agent
REDIS_URL=redis://:redis_password@redis:6379/0

# External APIs (Optional)
NEWS_API_KEY=your_news_api_key
TWITTER_API_KEY=your_twitter_api_key
REDDIT_CLIENT_ID=your_reddit_client_id
```

#### 3. Deploy with Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild and restart
docker-compose up --build -d
```

#### 4. Production Deployment
```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access monitoring
# Grafana: http://localhost:3001
# Prometheus: http://localhost:9090
```

## 🔧 Configuration

### Kalshi API Setup

1. **Create Kalshi Account**
   - Sign up at [Kalshi](https://kalshi.com/)

2. **Generate API Credentials**
   - Go to Account Settings → API Access
   - Generate API Key and Private Key
   - Set environment to sandbox (demo) or production

3. **RSA Key Authentication**
   ```bash
   # Generate RSA key pair
   openssl genrsa -out private_key.pem 2048
   openssl rsa -in private_key.pem -pubout -out public_key.pem

   # Upload public key to Kalshi
   # Add private key content to KALSHI_PRIVATE_KEY environment variable
   ```

### Database Configuration

#### PostgreSQL Setup
```bash
# Using Docker
docker run --name kalshi_postgres \
  -e POSTGRES_DB=kalshi_agent \
  -e POSTGRES_USER=kalshi_user \
  -e POSTGRES_PASSWORD=kalshi_password \
  -p 5432:5432 \
  -d postgres:14-alpine

# Using package manager
# Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib
sudo -u postgres createdb kalshi_agent
sudo -u postgres createuser kalshi_user
sudo -u postgres psql -c "ALTER USER kalshi_user PASSWORD 'kalshi_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE kalshi_agent TO kalshi_user;"
```

#### Redis Setup
```bash
# Using Docker
docker run --name kalshi_redis \
  -p 6379:6379 \
  -d redis:7-alpine redis-server --requirepass redis_password

# Using package manager
# Ubuntu/Debian:
sudo apt-get install redis-server
sudo systemctl start redis-server
```

## 🔒 Security Configuration

### Environment Variables Security
```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set secure database passwords
# Use strong passwords for production
```

### SSL/TLS Setup (Production)
```bash
# Use nginx reverse proxy with SSL
# Configure Let's Encrypt certificates
# Set up HTTPS redirects
```

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

## 📊 Monitoring and Logging

### Application Monitoring
```bash
# View application logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Monitor database
docker-compose logs -f postgres

# Monitor Redis
docker-compose logs -f redis
```

### Health Checks
```bash
# Backend health
curl http://localhost:8000/health

# Frontend health
curl http://localhost:3000

# Database health
docker-compose exec postgres pg_isready -U kalshi_user -d kalshi_agent
```

### Performance Monitoring
```bash
# System resources
docker stats

# Application metrics (if monitoring enabled)
curl http://localhost:9090/metrics
```

## 🚀 Production Deployment

### Using Docker Compose (Recommended)

#### 1. Server Preparation
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

#### 2. Application Deployment
```bash
# Clone repository
git clone <repository-url>
cd UX-builder

# Configure environment
cp .env.example .env
nano .env  # Edit with production values

# Deploy application
docker-compose -f docker-compose.yml --profile production up -d

# Set up SSL certificate (optional)
sudo certbot --nginx -d yourdomain.com
```

#### 3. SSL/HTTPS Setup
```bash
# Use nginx reverse proxy with SSL
# Configure nginx.conf for HTTPS
# Set up Let's Encrypt certificates
```

### Using Kubernetes

#### 1. Create Kubernetes Manifests
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: kalshi-agent
```

#### 2. Deploy Services
```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment
kubectl get pods -n kalshi-agent
kubectl get services -n kalshi-agent
```

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U kalshi_user -d kalshi_agent -c "SELECT 1;"
```

#### API Authentication Errors
```bash
# Verify Kalshi API credentials
# Check RSA key format
# Ensure environment variables are set correctly
```

#### Frontend Build Errors
```bash
# Clear node modules
rm -rf node_modules package-lock.json
npm install

# Check environment variables
cat .env
```

#### WebSocket Connection Issues
```bash
# Check WebSocket port accessibility
telnet localhost 8000

# Verify CORS configuration
# Check firewall settings
```

### Performance Issues

#### Slow API Response
```bash
# Check database query performance
# Monitor resource usage
# Optimize database indexes
```

#### Memory Issues
```bash
# Monitor memory usage
docker stats

# Adjust container memory limits
# Check for memory leaks
```

## 📈 Scaling

### Horizontal Scaling
```bash
# Scale backend services
docker-compose up --scale backend=3

# Use load balancer
# Configure database read replicas
```

### Database Optimization
```bash
# Add database indexes
# Optimize queries
# Use connection pooling
```

## 🔧 Maintenance

### Regular Tasks
```bash
# Update dependencies
cd backend && pip install -r requirements.txt --upgrade
cd frontend && npm update

# Backup database
docker-compose exec postgres pg_dump -U kalshi_user kalshi_agent > backup.sql

# Clean up old logs
docker-compose logs --tail=1000 > recent.log
```

### Monitoring
```bash
# Set up log rotation
# Monitor disk space
# Check application health
# Update security patches
```

## 📞 Support

For deployment issues:
1. Check the logs: `docker-compose logs -f`
2. Verify environment variables
3. Check network connectivity
4. Review this troubleshooting guide
5. Create an issue in the repository

---

**⚠️ Important**: Never commit API keys or sensitive credentials to version control. Always use environment variables for production deployments.
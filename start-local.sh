#!/bin/bash

# Kalshi Probability Analysis Agent - Local Development Startup Script
# This script sets up and starts the application for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Kalshi Probability Analysis Agent - Local Development${NC}"
echo "=================================================="

# Function to print colored status
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the correct directory
if [ ! -f "docker-compose.yml" ]; then
    print_error "Please run this script from the UX-builder directory"
    exit 1
fi

# Check dependencies
print_status "Checking dependencies..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed"
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js is required but not installed"
    exit 1
fi

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm is required but not installed"
    exit 1
fi

print_status "Dependencies check passed ✓"

# Backend setup
print_status "Setting up backend..."
cd backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    print_status "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade pip
pip install --upgrade pip

# Install requirements
print_status "Installing Python dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found, creating from template..."
    cp .env.example .env
    print_warning "Please edit backend/.env with your Kalshi API credentials"
    print_warning "Required variables: KALSHI_API_KEY, KALSHI_PRIVATE_KEY"
    print_warning "Database setup: DATABASE_URL, REDIS_URL"
fi

cd ..

# Frontend setup
print_status "Setting up frontend..."
cd frontend

# Install npm dependencies
print_status "Installing Node.js dependencies..."
npm install

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found, creating from template..."
    cp .env.example .env
    print_warning "Please edit frontend/.env with your API URLs"
fi

cd ..

# Check for PostgreSQL and Redis
print_status "Checking for required services..."

if command -v psql &> /dev/null; then
    print_status "PostgreSQL found ✓"
else
    print_warning "PostgreSQL not found. Please install PostgreSQL or use Docker:"
    echo "docker run --name kalshi_postgres -e POSTGRES_DB=kalshi_agent -e POSTGRES_USER=kalshi_user -e POSTGRES_PASSWORD=kalshi_password -p 5432:5432 -d postgres:14-alpine"
fi

if command -v redis-server &> /dev/null; then
    print_status "Redis found ✓"
else
    print_warning "Redis not found. Please install Redis or use Docker:"
    echo "REDIS_PASSWORD=redis_password"
    echo "docker run --name kalshi_redis -p 6379:6379 -d redis:7-alpine redis-server --requirepass \${REDIS_PASSWORD}"
fi

# Create startup scripts
print_status "Creating startup scripts..."

# Backend startup script
cat > start-backend.sh << 'EOF'
#!/bin/bash
cd backend
source venv/bin/activate
echo "Starting backend server on http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
EOF

chmod +x start-backend.sh

# Frontend startup script
cat > start-frontend.sh << 'EOF'
#!/bin/bash
cd frontend
echo "Starting frontend on http://localhost:3000"
npm start
EOF

chmod +x start-frontend.sh

# Create stop script
cat > stop-services.sh << 'EOF'
#!/bin/bash
echo "Stopping all services..."
pkill -f "uvicorn app.main:app"
pkill -f "npm start"
pkill -f "node.*start"
echo "Services stopped."
EOF

chmod +x stop-services.sh

print_status "Setup complete! ✓"
echo ""
echo -e "${GREEN}🎉 Kalshi Probability Analysis Agent is ready for local development!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Configure your environment variables:"
echo "   - Edit backend/.env with your Kalshi API credentials"
echo "   - Edit frontend/.env with your API URLs"
echo "   - Set up DATABASE_URL and REDIS_URL in backend/.env"
echo ""
echo "2. Start the services:"
echo "   - Terminal 1: ./start-backend.sh"
echo "   - Terminal 2: ./start-frontend.sh"
echo "   - Terminal 3 (optional): Start PostgreSQL and Redis"
echo ""
echo "3. Access the application:"
echo "   - Frontend: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}⚠️  Remember:${NC}"
echo "- Never commit API keys to version control"
echo "- Use sandbox environment for testing"
echo "- Check the logs for any issues"
echo ""
echo "To stop all services, run: ./stop-services.sh"
echo ""
echo -e "${BLUE}Happy trading! 📈${NC}"
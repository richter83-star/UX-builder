# Kalshi Probability Analysis Agent

A sophisticated probability analysis agent that integrates with Kalshi prediction markets to provide users with enhanced winning probabilities through ensemble analysis, adaptive risk management, and intelligent recommendation systems.

## 🚀 Features

### Core Functionality
- **Real-time Kalshi API Integration** with RSA-PSS authentication
- **Multi-method Ensemble Analysis** combining sentiment, statistical, and ML models
- **Adaptive Risk Management** with user-configurable controls
- **Web Dashboard** with live updates via WebSocket
- **Optional Automated Trading** with strict safety constraints
- **Comprehensive Performance Tracking** and visualization

### Analysis Methods
- **Sentiment Analysis**: Twitter, Reddit, and news sentiment aggregation
- **Statistical Analysis**: Technical indicators, pattern recognition, mean reversion
- **Machine Learning**: Random Forest, Gradient Boosting, LSTM, ARIMA models
- **Ensemble Combination**: Dynamic weight optimization and confidence weighting

### Risk Management
- Maximum position sizing (5% of portfolio by default)
- Category exposure limits (20% per category)
- Daily loss limits (2% of portfolio)
- Kelly Criterion position sizing with fractional Kelly
- Stop-loss rules and correlation monitoring
- Emergency stop functionality

## 📋 System Requirements

- Python 3.9+
- Node.js 18+
- PostgreSQL 12+
- Redis 6+
- Docker & Docker Compose (recommended)

## 🛠️ Installation

### Option 1: Docker Compose (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd UX-builder
   ```

2. **Set up environment variables**
   ```bash
   # Copy environment templates
   cp backend/.env.example .env
   cp frontend/.env.example frontend/.env

   # Edit .env file with your configuration
   nano .env
   ```

3. **Start the application**
   ```bash
   # Start all services
   docker-compose up -d

   # Or start with monitoring
   docker-compose --profile monitoring up -d
   ```

   > **Note:** Redis now binds to `${REDIS_HOST_PORT:-6380}` to avoid conflicts with local Redis instances. Set `REDIS_HOST_PORT=6379` (or another open port) in your `.env` if you need a different mapping.

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs
   - Grafana (if enabled): http://localhost:3001

### Option 2: Manual Installation

#### Backend Setup

1. **Install Python dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Set up database**
   ```bash
   # Create PostgreSQL database
   createdb kalshi_agent

   # Run migrations (if using Alembic)
   alembic upgrade head
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Start the backend**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

#### Frontend Setup

1. **Install Node.js dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the frontend**
   ```bash
   npm start
   ```

## ⚙️ Configuration

### Required Environment Variables

#### Backend Configuration
```bash
# Kalshi API Configuration
KALSHI_API_KEY=your_api_key_here
KALSHI_PRIVATE_KEY=your_private_key_here
KALSHI_PRIVATE_KEY_FILE=/optional/path/to/private_key.pem
KALSHI_PRIVATE_KEY_BASE64=optional_base64_encoded_private_key
KALSHI_ENVIRONMENT=sandbox  # sandbox or production

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/kalshi_agent
REDIS_URL=redis://localhost:6379/0

# Security
SECRET_KEY=your_secret_key_here_change_in_production
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# External API Keys (optional, for sentiment analysis)
NEWS_API_KEY=your_news_api_key
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

#### Frontend Configuration
```bash
# API Configuration
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000

# Feature Flags
REACT_APP_ENABLE_AUTO_TRADING=false
REACT_APP_ENABLE_ADVANCED_CHARTS=true
REACT_APP_ENABLE_NOTIFICATIONS=true
```

### Kalshi API Setup

1. **Create a Kalshi account** at [Kalshi](https://kalshi.com/)
2. **Generate API keys** in your account settings
3. **Create RSA key pair** for authentication:
   ```bash
   openssl genrsa -out private_key.pem 2048
   openssl rsa -in private_key.pem -pubout -out public_key.pem
   ```
4. **Upload public key** to Kalshi and configure API access
5. **Handling Docker Compose .env files**: multiline private keys can break parsing. Either mount a key file and set `KALSHI_PRIVATE_KEY_FILE`, or encode your key to a single line and set `KALSHI_PRIVATE_KEY_BASE64` (e.g., `base64 -w0 private_key.pem`).

## 📊 Usage

### Getting Started

1. **Register/Login** to the web dashboard
2. **Configure your risk profile** (conservative, moderate, aggressive)
3. **Connect your Kalshi account** with API credentials
4. **View market opportunities** in the dashboard
5. **Analyze specific markets** with detailed ensemble analysis
6. **Execute trades** manually or enable automated trading

### Main Features

#### Dashboard
- Real-time portfolio overview
- Performance charts and metrics
- Risk monitoring and alerts
- Top trading opportunities

#### Market Analysis
- Browse available Kalshi markets
- Detailed ensemble analysis
- Individual model breakdowns
- Historical performance tracking

#### Trading
- Manual order placement
- Risk assessment before trades
- Position management
- Portfolio allocation tracking

#### Risk Management
- Configure risk parameters
- Monitor exposure limits
- Emergency stop functionality
- Risk alerts and notifications

## 🔧 Development

### Project Structure
```
UX-builder/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API endpoints
│   │   ├── core/           # Core business logic
│   │   │   ├── analyzers/  # Analysis engines
│   │   │   ├── kalshi_client.py
│   │   │   ├── risk_manager.py
│   │   │   └── portfolio.py
│   │   ├── models/         # Database models
│   │   └── utils/          # Utilities
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── hooks/          # Custom hooks
│   │   ├── services/       # API services
│   │   └── types/          # TypeScript types
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml      # Docker configuration
└── README.md
```

### Running Tests

#### Backend Tests
```bash
cd backend
pytest tests/ -v --cov=app
```

#### Frontend Tests
```bash
cd frontend
npm test
```

### Code Quality

#### Backend
```bash
# Format code
black app/
isort app/

# Lint code
flake8 app/
mypy app/
```

#### Frontend
```bash
# Format code
npm run lint:fix

# Type check
npm run type-check
```

## 📈 Performance Metrics

The system aims to achieve:
- **API Response Time**: < 200ms (95th percentile)
- **WebSocket Latency**: < 500ms for real-time updates
- **Ensemble Model Accuracy**: > 70% on binary predictions
- **Win Rate Target**: > 65% on executed trades
- **Maximum Drawdown**: < 15%
- **Annual Return Target**: > 20%

## 🔒 Security

- RSA-PSS authentication for Kalshi API
- JWT-based authentication for web interface
- Environment variable configuration
- Rate limiting and circuit breakers
- Comprehensive input validation
- Secure WebSocket connections

## 📝 API Documentation

### Authentication
All API endpoints require JWT authentication:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/markets
```

### Key Endpoints

#### Markets
- `GET /api/markets` - List available markets
- `GET /api/markets/{id}` - Get market details
- `GET /api/markets/{id}/history` - Get price history

#### Analysis
- `POST /api/analysis/refresh` - Trigger analysis
- `GET /api/analysis/opportunities` - Get opportunities
- `GET /api/analysis/{id}` - Get market analysis

#### Trading
- `POST /api/trading/orders` - Place order
- `GET /api/trading/positions` - Get positions
- `GET /api/trading/portfolio/metrics` - Get portfolio metrics

#### WebSocket
- `WS /ws` - Real-time updates
  - Subscribe to market updates
  - Portfolio updates
  - Risk alerts
  - Trade notifications

Full API documentation available at: http://localhost:8000/docs

## 🐛 Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check logs
docker-compose logs postgres
```

#### WebSocket Connection Issues
- Check firewall settings
- Verify CORS configuration
- Ensure WebSocket port is accessible

#### Authentication Errors
- Verify JWT token is valid
- Check API key configuration
- Ensure user account is active

### Logs

#### Backend Logs
```bash
docker-compose logs -f backend
```

#### Frontend Logs
Check browser developer console

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

- 📧 Email: support@kalshi-agent.com
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 📖 Documentation: [Wiki](https://github.com/your-repo/wiki)

## 🙏 Acknowledgments

- [Kalshi](https://kalshi.com/) for the prediction markets platform
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework
- [React](https://reactjs.org/) for the frontend framework
- [Ant Design](https://ant.design/) for UI components
- All contributors and beta testers

---

**⚠️ Disclaimer**: This software is for educational and research purposes. Trading prediction markets involves substantial risk. Past performance is not indicative of future results. Always do your own research and trade responsibly.
## Early access operations

Run the lightweight migration helper to create watchlist/risk tables:

```bash
cd backend
python -c "from app.models.migrations import run_migrations; run_migrations()"
```

Run targeted tests:

```bash
cd backend
pytest
```

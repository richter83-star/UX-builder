from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn

from app.utils.config import settings
from app.utils.logging import setup_logging
from app.api.endpoints import markets, analysis, trading, auth
from app.api.endpoints import watchlist, rules, admin, market_requests
from app.api.websocket import websocket_router
from app.models.database import engine, Base
from app.core.tasks import start_background_jobs

# Setup logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Kalshi Probability Analysis Agent")

    # Create database tables in non-production environments when explicitly enabled
    if settings.AUTO_CREATE_TABLES:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully (auto-create enabled)")
    else:
        logger.info("Skipping automatic table creation; run migrations instead")

    # Start background maintenance
    import asyncio

    asyncio.create_task(start_background_jobs())

    yield

    logger.info("Shutting down Kalshi Probability Analysis Agent")

# Create FastAPI application
app = FastAPI(
    title="Kalshi Probability Analysis Agent",
    description="Sophisticated probability analysis agent for Kalshi prediction markets",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(trading.router, prefix="/api/trading", tags=["trading"])
app.include_router(watchlist.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(rules.router, prefix="/api/rules", tags=["rules"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(market_requests.router, prefix="/api/market-requests", tags=["market-requests"])
app.include_router(websocket_router, prefix="/ws")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "Kalshi Probability Analysis Agent",
            "version": "1.0.0"
        }
    )


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(
        status_code=200,
        content={
            "message": "Kalshi Probability Analysis Agent API",
            "docs": "/docs",
            "health": "/health"
        }
    )

# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

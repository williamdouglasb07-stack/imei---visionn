from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZIPMiddleware
from contextlib import asynccontextmanager
import logging
import os

from config import settings
from database import init_db
from routes import auth, upload, search, dashboard

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerenciar lifecycle da aplicação"""
    # Startup
    logger.info("Starting up IMEI Vision API")
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down IMEI Vision API")


# Criar app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
)


# Middlewares
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# Compression
app.add_middleware(GZIPMiddleware, minimum_size=1000)


# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.PROJECT_VERSION,
        "service": settings.PROJECT_NAME
    }


# API v1
api_v1 = FastAPI(
    title=f"{settings.PROJECT_NAME} API v1",
    openapi_prefix=settings.API_V1_PREFIX
)

# Incluir rotas
api_v1.include_router(auth.router)
api_v1.include_router(upload.router)
api_v1.include_router(search.router)
api_v1.include_router(dashboard.router)

# Montar rotas na app principal
app.include_router(api_v1.router, prefix=settings.API_V1_PREFIX)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "description": settings.DESCRIPTION,
        "docs": "/docs",
        "health": "/health",
        "api_docs": f"{settings.API_V1_PREFIX}/docs"
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {
        "error": exc.detail,
        "status_code": exc.status_code
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "status_code": 500
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

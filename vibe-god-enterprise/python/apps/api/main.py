"""
Vibe-God Enterprise API Service
FastAPI application with enterprise-grade features
"""
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import structlog

from python.libs.observability import (
    configure_logging,
    init_tracing,
    init_metrics,
    get_logger,
    MetricsMiddleware,
)
from python.libs.security import get_auth_manager, get_rbac_manager, get_secrets_manager
from python.libs.database import init_database, close_database, get_db_session
from python.libs.resilience import get_circuit_breaker, get_bulkhead_registry
from python.libs.messaging import RabbitMQClient, RabbitMQConfig, KafkaClient, KafkaConfig

# Configure structured logging
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    json_output=os.getenv("LOG_FORMAT", "json") == "json",
    service_name="vibe-god-api",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
)

# Initialize tracing
init_tracing(
    service_name="vibe-god-api",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
    service_version=os.getenv("APP_VERSION", "1.0.0"),
)

# Initialize metrics
init_metrics(
    service_name="vibe-god-api",
    otlp_endpoint=os.getenv("OTLP_ENDPOINT"),
)

logger = get_logger(__name__)

# Global clients
rabbitmq_client: Optional[RabbitMQClient] = None
kafka_client: Optional[KafkaClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global rabbitmq_client, kafka_client

    logger.info("Starting Vibe-God API")

    # Initialize database
    await init_database()

    # Initialize secrets manager
    secrets_manager = get_secrets_manager()

    # Initialize RabbitMQ
    rabbitmq_config = RabbitMQConfig(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        username=os.getenv("RABBITMQ_USER", "guest"),
        password=await secrets_manager.get_secret_required("rabbitmq.password"),
        virtual_host=os.getenv("RABBITMQ_VHOST", "/"),
    )
    rabbitmq_client = RabbitMQClient(rabbitmq_config)
    await rabbitmq_client.connect()

    # Initialize Kafka
    kafka_config = KafkaConfig(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        client_id="vibe-god-api",
        group_id="vibe-god-api-group",
    )
    kafka_client = KafkaClient(kafka_config)
    await kafka_client.connect()

    # Initialize auth and RBAC
    get_auth_manager()
    get_rbac_manager()

    logger.info("Vibe-God API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Vibe-God API")

    if rabbitmq_client:
        await rabbitmq_client.disconnect()
    if kafka_client:
        await kafka_client.disconnect()

    await close_database()

    logger.info("Vibe-God API shut down complete")


# Create FastAPI app
app = FastAPI(
    title="Vibe-God Enterprise API",
    description="Enterprise-grade AI automation platform for Digital India",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan,
)

# Add middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health endpoints
@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """Liveness probe - returns 200 if process is alive."""
    return {"status": "alive"}


@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """Readiness probe - checks all dependencies."""
    from python.libs.database import get_database
    from python.libs.security import get_secrets_manager

    checks = {}

    # Database
    try:
        db = await get_database()
        checks["database"] = await db.health_check()
    except Exception as e:
        checks["database"] = False
        logger.error("Database health check failed", error=str(e))

    # Redis
    try:
        import redis.asyncio as redis
        redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = True
    except Exception as e:
        checks["redis"] = False
        logger.error("Redis health check failed", error=str(e))

    # RabbitMQ
    checks["rabbitmq"] = rabbitmq_client.is_connected if rabbitmq_client else False

    # Kafka
    checks["kafka"] = kafka_client.is_running if kafka_client else False

    # Ollama
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{os.getenv('OLLAMA_URL', 'http://localhost:11434')}/api/tags")
            checks["ollama"] = resp.status_code == 200
    except Exception as e:
        checks["ollama"] = False
        logger.error("Ollama health check failed", error=str(e))

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_healthy else "not ready",
            "checks": checks,
        },
    )


@app.get("/health/startup", tags=["Health"])
async def startup_check():
    """Startup probe - checks if application has started."""
    return {"status": "started"}


@app.get("/metrics", tags=["Monitoring"])
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


# API Routes
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint."""
    return {
        "name": "Vibe-God Enterprise API",
        "version": "1.0.0",
        "description": "Enterprise-grade AI automation platform for Digital India",
        "docs": "/docs",
        "health": "/health/ready",
        "metrics": "/metrics",
    }


# Example protected endpoint
@app.get("/api/v1/users/me", tags=["Users"])
async def get_current_user(
    current_user=Depends(get_auth_manager().get_current_active_user),
):
    """Get current authenticated user."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "roles": current_user.roles,
        "permissions": list(current_user.permissions),
    }


# Example admin endpoint
@app.get("/api/v1/admin/stats", tags=["Admin"])
async def get_admin_stats(
    current_user=Depends(get_auth_manager().require_role("admin")),
):
    """Get admin statistics."""
    from python.libs.database import get_database
    from python.libs.resilience import get_circuit_breaker, get_bulkhead_registry

    db = await get_database()
    pool_status = await db.get_pool_status()

    cb_registry = get_circuit_breaker("")
    circuit_breakers = cb_registry.get_all_metrics()

    bh_registry = get_bulkhead_registry()
    bulkheads = bh_registry.get_all_metrics()

    return {
        "database": pool_status,
        "circuit_breakers": circuit_breakers,
        "bulkheads": bulkheads,
    }


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        "HTTP exception",
        path=request.url.path,
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        workers=int(os.getenv("API_WORKERS", "1")),
        log_config=None,  # Use structlog
        access_log=False,
    )
"""
FastAPI application entrypoint.
"""

from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI, Request, status
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import ElasticsearchIKException
from app.core.logger import setup_logging


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise RAG backend API",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


setup_logging()


@app.exception_handler(ElasticsearchIKException)
async def es_ik_exception_handler(request: Request, exc: ElasticsearchIKException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "msg": exc.message,
            "error_type": "illegal_argument_exception",
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "msg": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "msg": "Request validation failed",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "msg": "Internal server error"},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Request: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(f"Response: {response.status_code} - Time: {process_time:.2f}ms")
        return response
    except Exception as exc:
        logger.error(f"Request failed: {exc}")
        raise


@app.get("/")
async def root():
    return {
        "message": "Welcome to RAG Backend API",
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


@app.get("/health/es")
async def es_health_check():
    from app.utils.es_client import es_client

    is_ok = await es_client.check_ik_analyzer()
    if is_ok:
        return {"status": "healthy", "analyzer": "ik_max_word"}

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "unhealthy", "msg": "IK analyzer is not available"},
    )


app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    from app.db.migrations import run_migrations
    from app.db.session import init_db
    from app.utils.es_client import es_client

    settings.validate_startup_configuration()

    if settings.INIT_DB_ON_STARTUP:
        logger.info("Running database migrations from startup hook")
        await asyncio.to_thread(run_migrations)
        await init_db()

    if not await es_client.check_ik_analyzer():
        logger.critical(
            "Elasticsearch IK analyzer is unavailable. Install the plugin before starting the service."
        )
        raise SystemExit(1)

    logger.info(f"[START] {settings.APP_NAME} v{settings.APP_VERSION} started")
    logger.info("[DOCS] http://localhost:8000/docs")
    logger.info("[HEALTH] http://localhost:8000/health")


@app.on_event("shutdown")
async def shutdown_event():
    from app.utils.es_client import es_client
    from app.utils.milvus_client import milvus_client
    from app.utils.redis_client import redis_client

    logger.info(f"[STOP] {settings.APP_NAME} shutting down")
    await redis_client.close()
    await es_client.close()
    await milvus_client.close()
    logger.info("[STOP] Async clients closed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )

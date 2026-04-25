"""Main FastAPI application for cloud explore service."""

import os
os.environ["PASSLIB_BCRYPT_TRUNCATE"] = "true"

import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import init_db
from app.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    print("=" * 50)
    print(f"Starting {settings.APP_NAME}")
    print(f"Version: {settings.APP_VERSION}")
    print("=" * 50)

    try:
        await init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        raise

    print("Application startup complete")
    yield

    print("Application shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Text Style Transfer Explore Service API - Share and discover style models",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests with timing."""
    start_time = time.time()
    method = request.method

    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        print(
            f"Request completed: {method} {request.url.path} | "
            f"Status: {response.status_code} | "
            f"Time: {process_time:.3f}s"
        )
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        process_time = time.time() - start_time
        print(f"Request failed: {method} {request.url.path} | Error: {str(e)} | Time: {process_time:.3f}s")
        raise


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
    )

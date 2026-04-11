"""Dependency injection for FastAPI."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Optional: Add authentication dependencies here if needed in future
# For v0.1, we don't require authentication

async def get_optional_user():
    """Get optional user (placeholder for future auth)."""
    return None

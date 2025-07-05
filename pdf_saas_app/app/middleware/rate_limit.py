from fastapi import Request, HTTPException, Response
from fastapi.responses import JSONResponse
import time
from pdf_saas_app.app.services.redis_service import redis_service
from pdf_saas_app.app.config import settings
import logging

logger = logging.getLogger(__name__)

class RateLimitMiddleware:
    """Middleware for rate limiting using Redis"""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Create request object
        request = Request(scope, receive)
        
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request.url.path):
            await self.app(scope, receive, send)
            return
        
        # Get client identifier (IP or user ID)
        client_id = self._get_client_id(request)
        
        # Check rate limit
        rate_limit_result = redis_service.check_rate_limit(
            key=f"rate_limit:{client_id}",
            max_requests=settings.RATE_LIMIT_REQUESTS,
            window=settings.RATE_LIMIT_WINDOW
        )
        
        if not rate_limit_result['allowed']:
            # Rate limit exceeded
            response_data = {
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_WINDOW} seconds",
                "reset_time": rate_limit_result['reset_time'],
                "remaining": rate_limit_result['remaining']
            }
            
            response = JSONResponse(
                status_code=429,
                content=response_data
            )
            
            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(settings.RATE_LIMIT_REQUESTS)
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_result['remaining'])
            response.headers["X-RateLimit-Reset"] = str(rate_limit_result['reset_time'])
            response.headers["Retry-After"] = str(rate_limit_result['reset_time'] - int(time.time()))
            
            await response(scope, receive, send)
            return
        
        # Add rate limit headers to successful responses
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                message["headers"].extend([
                    (b"X-RateLimit-Limit", str(settings.RATE_LIMIT_REQUESTS).encode()),
                    (b"X-RateLimit-Remaining", str(rate_limit_result['remaining']).encode()),
                    (b"X-RateLimit-Reset", str(rate_limit_result['reset_time']).encode()),
                ])
            await send(message)
        
        await self.app(scope, receive, send_with_headers)
    
    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if rate limiting should be skipped for this path"""
        skip_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/favicon.ico"
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def _get_client_id(self, request: Request) -> str:
        """Get client identifier for rate limiting"""
        # Try to get user ID from token first
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # For now, use IP as fallback. In a real implementation,
                # you'd decode the JWT and get the user ID
                pass
        except:
            pass
        
        # Use IP address as fallback
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Get the first IP in the chain
            client_ip = forwarded_for.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"
        
        return f"ip:{client_ip}"

def rate_limit_dependency(request: Request):
    """Dependency for manual rate limiting in specific endpoints"""
    if not settings.RATE_LIMIT_ENABLED:
        return
    
    # Get client identifier
    client_id = _get_client_id(request)
    
    # Check rate limit
    rate_limit_result = redis_service.check_rate_limit(
        key=f"rate_limit:{client_id}",
        max_requests=settings.RATE_LIMIT_REQUESTS,
        window=settings.RATE_LIMIT_WINDOW
    )
    
    if not rate_limit_result['allowed']:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Too many requests. Limit: {settings.RATE_LIMIT_REQUESTS} requests per {settings.RATE_LIMIT_WINDOW} seconds",
                "reset_time": rate_limit_result['reset_time'],
                "remaining": rate_limit_result['remaining']
            }
        )

def _get_client_id(request: Request) -> str:
    """Helper function to get client identifier"""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"
    
    return f"ip:{client_ip}" 
import functools
import hashlib
import json
from typing import Optional, Any, Callable
from app.services.redis_service import redis_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

def cache_response(ttl: int = None, key_prefix: str = "cache"):
    """
    Decorator to cache API responses
    
    Args:
        ttl: Time to live in seconds (defaults to CACHE_DEFAULT_TTL)
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if not settings.CACHE_ENABLED:
                return await func(*args, **kwargs)
            
            # Generate cache key
            cache_key = _generate_cache_key(func, key_prefix, args, kwargs)
            
            # Try to get from cache
            cached_result = redis_service.get_cache(cache_key)
            if cached_result is not None:
                logger.info(f"Cache hit for key: {cache_key}")
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            
            # Cache the result
            cache_ttl = ttl or settings.CACHE_DEFAULT_TTL
            redis_service.set_cache(cache_key, result, cache_ttl)
            logger.info(f"Cached result for key: {cache_key} (TTL: {cache_ttl}s)")
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache(pattern: str):
    """
    Decorator to invalidate cache after function execution
    
    Args:
        pattern: Cache key pattern to invalidate (e.g., "user:*", "doc:*")
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            if settings.CACHE_ENABLED:
                deleted_count = redis_service.clear_cache_pattern(pattern)
                logger.info(f"Invalidated {deleted_count} cache entries matching pattern: {pattern}")
            
            return result
        
        return wrapper
    return decorator

def _generate_cache_key(func: Callable, prefix: str, args: tuple, kwargs: dict) -> str:
    """Generate a unique cache key for the function call"""
    # Create a hash of the function name, args, and kwargs
    key_data = {
        'func': func.__name__,
        'module': func.__module__,
        'args': args,
        'kwargs': kwargs
    }
    
    # Convert to JSON string and hash it
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"{prefix}:{key_hash}"

class CacheManager:
    """Utility class for cache operations"""
    
    @staticmethod
    def clear_user_cache(user_id: str):
        """Clear all cache entries for a specific user"""
        if settings.CACHE_ENABLED:
            patterns = [
                f"user:{user_id}:*",
                f"doc:{user_id}:*",
                f"cache:*user:{user_id}*"
            ]
            
            total_deleted = 0
            for pattern in patterns:
                deleted = redis_service.clear_cache_pattern(pattern)
                total_deleted += deleted
            
            logger.info(f"Cleared {total_deleted} cache entries for user {user_id}")
    
    @staticmethod
    def clear_document_cache(document_id: str):
        """Clear cache entries for a specific document"""
        if settings.CACHE_ENABLED:
            patterns = [
                f"doc:{document_id}:*",
                f"cache:*doc:{document_id}*"
            ]
            
            total_deleted = 0
            for pattern in patterns:
                deleted = redis_service.clear_cache_pattern(pattern)
                total_deleted += deleted
            
            logger.info(f"Cleared {total_deleted} cache entries for document {document_id}")
    
    @staticmethod
    def get_cache_stats() -> dict:
        """Get cache statistics"""
        if not settings.CACHE_ENABLED:
            return {"enabled": False}
        
        try:
            # This would require Redis INFO command
            # For now, return basic info
            return {
                "enabled": True,
                "service_available": redis_service.is_available()
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {"enabled": True, "error": str(e)} 
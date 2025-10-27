import redis
import json
import time
from typing import Optional, Any, Dict, List
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class RedisService:
    """Service for Redis operations including caching and rate limiting"""
    
    def __init__(self):
        self.redis_client = None
        self.is_connected = False
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            if hasattr(settings, 'REDIS_URL') and settings.REDIS_URL:
                logger.info(f"Connecting to Redis using URL: {settings.REDIS_URL[:20]}...")
                self.redis_client = redis.from_url(settings.REDIS_URL)
            else:
                logger.warning("No REDIS_URL provided, Redis will be disabled")
                self.is_connected = False
                self.redis_client = None
                return
            
            # Test connection
            self.redis_client.ping()
            self.is_connected = True
            logger.info("Successfully connected to Redis")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {str(e)}")
            self.is_connected = False
            self.redis_client = None
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        if not self.is_connected or not self.redis_client:
            return False
        try:
            self.redis_client.ping()
            return True
        except:
            return False
    
    # Caching methods
    def set_cache(self, key: str, value: Any, expire: int = 3600) -> bool:
        """
        Set a value in cache with expiration
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expire: Expiration time in seconds (default: 1 hour)
        """
        if not self.is_available():
            return False
        
        try:
            serialized_value = json.dumps(value)
            return self.redis_client.setex(key, expire, serialized_value)
        except Exception as e:
            logger.error(f"Error setting cache for key {key}: {str(e)}")
            return False
    
    def get_cache(self, key: str) -> Optional[Any]:
        """
        Get a value from cache
        Args:
            key: Cache key
        Returns:
            Cached value or None if not found
        """
        if not self.is_available():
            return None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting cache for key {key}: {str(e)}")
            return None
    
    def delete_cache(self, key: str) -> bool:
        """Delete a value from cache"""
        if not self.is_available():
            return False
        
        try:
            return bool(self.redis_client.delete(key))
        except Exception as e:
            logger.error(f"Error deleting cache for key {key}: {str(e)}")
            return False
    
    def clear_cache_pattern(self, pattern: str) -> int:
        """
        Clear cache entries matching a pattern
        Args:
            pattern: Redis pattern (e.g., "user:*", "doc:*")
        Returns:
            Number of keys deleted
        """
        if not self.is_available():
            return 0
        
        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Error clearing cache pattern {pattern}: {str(e)}")
            return 0
    
    # Rate limiting methods
    def check_rate_limit(self, key: str, max_requests: int, window: int) -> Dict[str, Any]:
        """
        Check rate limit for a given key
        Args:
            key: Rate limit key (usually user_id or IP)
            max_requests: Maximum requests allowed in window
            window: Time window in seconds
        Returns:
            Dict with 'allowed' (bool) and 'remaining' (int) keys
        """
        if not self.is_available():
            return {'allowed': True, 'remaining': max_requests}
        
        try:
            current_time = int(time.time())
            window_start = current_time - window
            
            # Add current request
            self.redis_client.zadd(key, {str(current_time): current_time})
            
            # Remove old requests outside the window
            self.redis_client.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            request_count = self.redis_client.zcard(key)
            
            # Set expiration on the key
            self.redis_client.expire(key, window)
            
            allowed = request_count <= max_requests
            remaining = max(0, max_requests - request_count)
            
            return {
                'allowed': allowed,
                'remaining': remaining,
                'reset_time': current_time + window
            }
        except Exception as e:
            logger.error(f"Error checking rate limit for key {key}: {str(e)}")
            return {'allowed': True, 'remaining': max_requests}
    
    def get_rate_limit_info(self, key: str) -> Dict[str, Any]:
        """Get current rate limit information for a key"""
        if not self.is_available():
            return {'requests': 0, 'reset_time': 0}
        
        try:
            request_count = self.redis_client.zcard(key)
            ttl = self.redis_client.ttl(key)
            return {
                'requests': request_count,
                'reset_time': int(time.time()) + ttl if ttl > 0 else 0
            }
        except Exception as e:
            logger.error(f"Error getting rate limit info for key {key}: {str(e)}")
            return {'requests': 0, 'reset_time': 0}
    
    # Session management
    def set_session(self, session_id: str, data: Dict[str, Any], expire: int = 86400) -> bool:
        """
        Store session data
        Args:
            session_id: Session identifier
            data: Session data
            expire: Expiration time in seconds (default: 24 hours)
        """
        return self.set_cache(f"session:{session_id}", data, expire)
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        return self.get_cache(f"session:{session_id}")
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session data"""
        return self.delete_cache(f"session:{session_id}")
    
    # Document processing queue
    def add_to_queue(self, queue_name: str, task_data: Dict[str, Any]) -> bool:
        """
        Add a task to a processing queue
        Args:
            queue_name: Name of the queue
            task_data: Task data to add
        """
        if not self.is_available():
            return False
        
        try:
            task_id = f"{queue_name}:{int(time.time() * 1000)}"
            self.redis_client.lpush(queue_name, json.dumps({
                'id': task_id,
                'data': task_data,
                'timestamp': time.time()
            }))
            return True
        except Exception as e:
            logger.error(f"Error adding to queue {queue_name}: {str(e)}")
            return False
    
    def get_from_queue(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Get next task from queue"""
        if not self.is_available():
            return None
        
        try:
            task = self.redis_client.rpop(queue_name)
            if task:
                return json.loads(task)
            return None
        except Exception as e:
            logger.error(f"Error getting from queue {queue_name}: {str(e)}")
            return None
    
    # Health check
    def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            if not self.is_available():
                return {'status': 'unavailable', 'error': 'Redis not connected'}
            
            # Test basic operations
            test_key = 'health_check_test'
            test_value = {'test': True, 'timestamp': time.time()}
            
            # Test set
            set_result = self.set_cache(test_key, test_value, 10)
            if not set_result:
                return {'status': 'error', 'error': 'Failed to set cache'}
            
            # Test get
            get_result = self.get_cache(test_key)
            if get_result != test_value:
                return {'status': 'error', 'error': 'Failed to get cache'}
            
            # Test delete
            delete_result = self.delete_cache(test_key)
            if not delete_result:
                return {'status': 'error', 'error': 'Failed to delete cache'}
            
            return {'status': 'healthy', 'message': 'All Redis operations working'}
            
        except Exception as e:
            return {'status': 'error', 'error': str(e)}

# Global Redis service instance
redis_service = RedisService() 
# app/cache.py
"""
Flask-Caching configuration for KickthisUSs.
Provides caching for frequently accessed data to improve performance.
"""

from flask_caching import Cache

# Initialize cache instance
cache = Cache()


def init_cache(app):
    """
    Initialize Flask-Caching with the Flask app.
    
    Configuration options:
    - CACHE_TYPE: 'simple' for development, 'redis' for production
    - CACHE_DEFAULT_TIMEOUT: Default cache timeout in seconds
    - CACHE_REDIS_URL: Redis URL for production caching
    """
    # Default configuration
    cache_config = {
        'CACHE_TYPE': app.config.get('CACHE_TYPE', 'SimpleCache'),
        'CACHE_DEFAULT_TIMEOUT': app.config.get('CACHE_DEFAULT_TIMEOUT', 300),  # 5 minutes
    }
    
    # Use Redis in production if available
    redis_url = app.config.get('CACHE_REDIS_URL') or app.config.get('REDIS_URL')
    if redis_url and app.config.get('FLASK_ENV') == 'production':
        cache_config['CACHE_TYPE'] = 'RedisCache'
        cache_config['CACHE_REDIS_URL'] = redis_url
    
    # Apply configuration
    app.config.from_mapping(cache_config)
    
    # Initialize cache with app
    cache.init_app(app)
    
    app.logger.info(f"Cache initialized: Type={cache_config['CACHE_TYPE']}, Timeout={cache_config['CACHE_DEFAULT_TIMEOUT']}s")
    
    return cache


# ============================================
# Cache Key Generators
# ============================================

def make_project_cache_key(project_id: int) -> str:
    """Generate cache key for project data."""
    return f"project:{project_id}"


def make_user_cache_key(user_id: int) -> str:
    """Generate cache key for user data."""
    return f"user:{user_id}"


def make_project_structure_key(project_id: int) -> str:
    """Generate cache key for project structure (Hub Agents)."""
    return f"project_structure:{project_id}"


def make_document_cache_key(project_id: int, filename: str) -> str:
    """Generate cache key for document content."""
    return f"doc:{project_id}:{filename}"


# ============================================
# Cache Decorators for Common Patterns
# ============================================

def cached_project_data(timeout: int = 300):
    """
    Decorator for caching project-related data.
    
    Usage:
        @cached_project_data(timeout=600)
        def get_project_stats(project_id):
            ...
    """
    def decorator(f):
        from functools import wraps
        
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Extract project_id from args or kwargs
            project_id = kwargs.get('project_id') or (args[0] if args else None)
            if project_id is None:
                return f(*args, **kwargs)
            
            cache_key = f"project_data:{f.__name__}:{project_id}"
            
            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout=timeout)
            return result
        
        return decorated_function
    return decorator


# ============================================
# Cache Invalidation Helpers
# ============================================

def invalidate_project_cache(project_id: int):
    """Invalidate all cached data for a project."""
    patterns = [
        make_project_cache_key(project_id),
        make_project_structure_key(project_id),
        f"project_data:*:{project_id}",
    ]
    for pattern in patterns:
        try:
            cache.delete(pattern)
        except Exception:
            pass  # Ignore errors during cache invalidation


def invalidate_user_cache(user_id: int):
    """Invalidate all cached data for a user."""
    try:
        cache.delete(make_user_cache_key(user_id))
    except Exception:
        pass


def invalidate_document_cache(project_id: int, filename: str = None):
    """Invalidate document cache for a project."""
    if filename:
        cache.delete(make_document_cache_key(project_id, filename))
    else:
        # Invalidate all documents for this project
        # Note: This requires pattern matching which may not work with SimpleCache
        try:
            cache.delete(f"doc:{project_id}:*")
        except Exception:
            pass


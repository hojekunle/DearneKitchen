import functools
import logging

from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages

logger = logging.getLogger(__name__)


def rate_limit(key_prefix, limit=5, period=300):
    """Simple cache-based rate limiter (limit requests per period in seconds)."""

    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.user.is_authenticated:
                identifier = f"user:{request.user.pk}"
            else:
                identifier = f"ip:{request.META.get('REMOTE_ADDR', 'unknown')}"

            cache_key = f"ratelimit:{key_prefix}:{identifier}"
            count = cache.get(cache_key, 0)
            if count >= limit:
                logger.warning('Rate limit exceeded for %s on %s', identifier, key_prefix)
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse(
                        {'error': 'Too many requests. Please try again later.'},
                        status=429,
                    )
                messages.error(request, 'Too many requests. Please try again in a few minutes.')
                return redirect(request.META.get('HTTP_REFERER', '/'))

            cache.set(cache_key, count + 1, period)
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator

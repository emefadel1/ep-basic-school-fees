# middleware/security.py

import logging
from django.http import JsonResponse
from django.core.cache import cache

logger = logging.getLogger('security')

class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 1. Check IP blacklist
        client_ip = self.get_client_ip(request)
        if cache.get(f'blocked_ip:{client_ip}'):
            logger.warning(f"Blocked IP attempted access: {client_ip}")
            return JsonResponse(
                {'error': 'Access denied'},
                status=403
            )
        
        # 2. Validate content type for POST/PUT
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type
            if content_type and 'application/json' not in content_type:
                if 'multipart/form-data' not in content_type:
                    return JsonResponse(
                        {'error': 'Invalid content type'},
                        status=415
                    )
        
        response = self.get_response(request)
        
        # 3. Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class LoginAttemptMiddleware:
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.path == '/api/auth/login/' and request.method == 'POST':
            client_ip = self.get_client_ip(request)
            cache_key = f'login_attempts:{client_ip}'
            
            attempts = cache.get(cache_key, 0)
            if attempts >= self.MAX_ATTEMPTS:
                logger.warning(f"Login locked for IP: {client_ip}")
                return JsonResponse({
                    'error': 'Too many login attempts. Try again later.',
                    'retry_after': self.LOCKOUT_DURATION
                }, status=429)
        
        return self.get_response(request)
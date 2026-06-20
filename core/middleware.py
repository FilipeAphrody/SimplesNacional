import threading

_thread_locals = threading.local()

def get_current_company():
    """
    Retrieves the company from thread local storage.
    This ensures that queries are automatically scoped to the current user's active tenant.
    """
    return getattr(_thread_locals, 'company', None)

class TenantMiddleware:
    """
    Intercepts every HTTP request, identifies the user's active company,
    and binds it to thread-local storage for Dynamic Least Privilege enforcement.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            company_user = request.user.companies.first()
            if company_user:
                _thread_locals.company = company_user.company
            else:
                _thread_locals.company = None
        else:
            _thread_locals.company = None
            
        response = self.get_response(request)
        
        # Cleanup to prevent data leakage between requests on the same thread
        if hasattr(_thread_locals, 'company'):
            del _thread_locals.company
            
        return response

class AdminAccessMiddleware:
    """
    Strictly restricts access to any /admin/ or /superadmin/ routes based on a whitelist of IP addresses.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.conf import settings
        from django.http import HttpResponseForbidden
        
        # Check if the path is an admin path
        is_admin_path = request.path.startswith(f'/{settings.ADMIN_URL}') or request.path.startswith('/superadmin/')
        
        if is_admin_path:
            client_ip = request.META.get('HTTP_X_FORWARDED_FOR')
            if client_ip:
                client_ip = client_ip.split(',')[0].strip()
            else:
                client_ip = request.META.get('REMOTE_ADDR')
                
            # If IP is not in the ALLOWED_ADMIN_IPS, instantly block it.
            if client_ip not in settings.ALLOWED_ADMIN_IPS:
                return HttpResponseForbidden("Access Denied: Your IP is not whitelisted for admin access.")
                
        return self.get_response(request)

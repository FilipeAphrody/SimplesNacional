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

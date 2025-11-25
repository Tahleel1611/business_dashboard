from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from functools import wraps

# Decorator to check if user is authenticated
def login_required_custom(view_func):
    """Check if user is authenticated"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated')
        return view_func(request, *args, **kwargs)
    return wrapper


# Decorator to check specific roles
def role_required(*roles):
    """Check if user has one of the specified roles"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return HttpResponseForbidden('Not authenticated')
            if hasattr(request.user, 'role') and request.user.role not in roles:
                return HttpResponseForbidden('Permission denied: insufficient role')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Specific role decorators
def admin_required(view_func):
    """Only admin users can access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated')
        if not hasattr(request.user, 'role') or request.user.role != 'admin':
            return HttpResponseForbidden('Admin access required')
        return view_func(request, *args, **kwargs)
    return wrapper


def manager_or_admin_required(view_func):
    """Only manager and admin users can access"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated')
        if not hasattr(request.user, 'role') or request.user.role not in ['manager', 'admin']:
            return HttpResponseForbidden('Manager or Admin access required')
        return view_func(request, *args, **kwargs)
    return wrapper

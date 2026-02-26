from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(min_role):
    """Decorator: 'admin' requires admin, 'operator' requires admin or operator."""
    role_hierarchy = {"viewer": 0, "operator": 1, "admin": 2}

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            user_level = role_hierarchy.get(request.user.role, 0)
            required_level = role_hierarchy.get(min_role, 0)
            if user_level < required_level:
                messages.error(request, "You do not have permission to access this page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

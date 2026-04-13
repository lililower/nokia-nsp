from django.shortcuts import redirect
from django.urls import reverse


class ForcePasswordChangeMiddleware:
    """Redirect users with force_password_change=True to the change password page."""

    EXEMPT_URLS = [
        "change_password",
        "logout",
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.user.is_authenticated
            and hasattr(request.user, "force_password_change")
            and request.user.force_password_change
        ):
            url_name = request.resolver_match.url_name if request.resolver_match else ""
            if url_name not in self.EXEMPT_URLS:
                return redirect("change_password")

        return self.get_response(request)

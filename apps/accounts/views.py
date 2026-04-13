from django.contrib import messages
from django.contrib.auth import login, views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .decorators import role_required
from .forms import ChangePasswordForm, LoginForm, ProfileForm, UserCreateForm
from .models import AuditLog, User

# Lock account for 15 minutes after 5 failed attempts
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class CustomLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm

    def form_valid(self, form):
        user = form.get_user()
        # Check lockout
        if user.is_locked:
            messages.error(self.request, "Account is locked due to too many failed attempts. Try again later.")
            AuditLog.log(self.request, "login_failed", f"Locked account login attempt: {user.username}")
            return self.form_invalid(form)

        # Reset failed attempts on success
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])

        AuditLog.log(self.request, "login", f"User logged in", target_object=f"User:{user.pk}")

        response = super().form_valid(form)

        # Redirect to password change if forced
        if user.force_password_change:
            return redirect("change_password")

        return response

    def form_invalid(self, form):
        # Track failed login attempts
        username = form.cleaned_data.get("username", "") if hasattr(form, "cleaned_data") else ""
        if not username:
            username = self.request.POST.get("username", "")

        if username:
            try:
                user = User.objects.get(username=username)
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                    user.locked_until = timezone.now() + timezone.timedelta(minutes=LOCKOUT_MINUTES)
                    messages.error(
                        self.request,
                        f"Account locked for {LOCKOUT_MINUTES} minutes after {MAX_FAILED_ATTEMPTS} failed attempts."
                    )
                user.save(update_fields=["failed_login_attempts", "locked_until"])
            except User.DoesNotExist:
                pass

            AuditLog.log(self.request, "login_failed", f"Failed login for: {username}")

        return super().form_invalid(form)


class CustomLogoutView(auth_views.LogoutView):
    next_page = "login"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            AuditLog.log(request, "logout", "User logged out")
        return super().dispatch(request, *args, **kwargs)


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect("profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})


@login_required
def change_password(request):
    if request.method == "POST":
        form = ChangePasswordForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            user.force_password_change = False
            user.save(update_fields=["force_password_change"])
            # Re-login to refresh session
            login(request, user)
            AuditLog.log(request, "password_change", "Password changed", target_object=f"User:{user.pk}")
            messages.success(request, "Password changed successfully.")
            return redirect("dashboard")
    else:
        form = ChangePasswordForm(request.user)
    return render(request, "accounts/change_password.html", {"form": form})


@login_required
@role_required("admin")
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            AuditLog.log(
                request, "user_create",
                f"Created user '{user.username}' with role '{user.role}'",
                target_object=f"User:{user.pk}",
            )
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect("dashboard")
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_create.html", {"form": form})


@login_required
@role_required("admin")
def user_list(request):
    users = User.objects.all().order_by("username")
    return render(request, "accounts/user_list.html", {"users": users})


@login_required
@role_required("admin")
def audit_log_view(request):
    """View audit logs with filtering."""
    logs = AuditLog.objects.all()

    # Filters
    action_filter = request.GET.get("action", "")
    user_filter = request.GET.get("user", "")
    date_from = request.GET.get("from", "")
    date_to = request.GET.get("to", "")

    if action_filter:
        logs = logs.filter(action=action_filter)
    if user_filter:
        logs = logs.filter(username__icontains=user_filter)
    if date_from:
        logs = logs.filter(timestamp__date__gte=date_from)
    if date_to:
        logs = logs.filter(timestamp__date__lte=date_to)

    logs = logs[:500]

    action_choices = AuditLog.ACTION_CHOICES
    users = User.objects.values_list("username", flat=True).distinct()

    return render(request, "accounts/audit_log.html", {
        "logs": logs,
        "action_choices": action_choices,
        "users": users,
        "action_filter": action_filter,
        "user_filter": user_filter,
        "date_from": date_from,
        "date_to": date_to,
    })


@login_required
@role_required("admin")
def unlock_user(request, pk):
    """Admin action to unlock a locked user account."""
    if request.method == "POST":
        user = User.objects.get(pk=pk)
        user.failed_login_attempts = 0
        user.locked_until = None
        user.save(update_fields=["failed_login_attempts", "locked_until"])
        AuditLog.log(request, "other", f"Unlocked account '{user.username}'", target_object=f"User:{pk}")
        messages.success(request, f"Account '{user.username}' unlocked.")
    return redirect("user_list")

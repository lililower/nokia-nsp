from django.contrib.auth import login, views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render

from .decorators import role_required
from .forms import LoginForm, ProfileForm, UserCreateForm


class CustomLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm


class CustomLogoutView(auth_views.LogoutView):
    next_page = "login"


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
@role_required("admin")
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"User '{user.username}' created successfully.")
            return redirect("dashboard")
    else:
        form = UserCreateForm()
    return render(request, "accounts/user_create.html", {"form": form})

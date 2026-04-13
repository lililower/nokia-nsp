from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.CustomLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("change-password/", views.change_password, name="change_password"),
    path("users/", views.user_list, name="user_list"),
    path("users/create/", views.user_create, name="user_create"),
    path("users/<int:pk>/unlock/", views.unlock_user, name="unlock_user"),
    path("audit-log/", views.audit_log_view, name="audit_log"),
]

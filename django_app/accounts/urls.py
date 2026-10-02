from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.ThemedLoginView.as_view(), name="login"),
    path("logout/", views.ThemedLogoutView.as_view(), name="logout"),
    path("profile/", views.profile, name="profile"),
    path("denied/", views.staff_denied, name="staff_denied"),
    path("dashboard/", views.demand_dashboard, name="demand_dashboard"),
    path("moderate-review/", views.moderate_review, name="moderate_review"),
    path("set-language/", views.set_language, name="set_language"),
    path("set-theme/", views.set_theme, name="set_theme"),
]

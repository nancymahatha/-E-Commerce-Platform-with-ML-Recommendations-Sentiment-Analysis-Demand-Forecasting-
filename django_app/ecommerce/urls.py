"""Root URL configuration.

Each app owns its own urls.py and is mounted here under a prefix:
  /            -> products (home + shop)
  /cart/       -> cart
  /orders/     -> orders
  /reviews/    -> reviews
  /accounts/   -> auth, profile, dashboard, toggles
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("products.urls")),
    path("cart/", include("cart.urls")),
    path("orders/", include("orders.urls")),
    path("reviews/", include("reviews.urls")),
    path("accounts/", include("accounts.urls")),
]

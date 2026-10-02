from django.urls import path
from . import admin_views, views

app_name = "products"

urlpatterns = [
    path("", views.home, name="home"),
    path("shop/", views.product_list, name="shop"),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),

    # ---- in-site store admin (staff only) ----
    path("manage/", admin_views.store_admin, name="admin_home"),
    path("manage/products/", admin_views.product_admin_list, name="admin_list"),
    path("manage/products/add/", admin_views.product_admin_create, name="admin_create"),
    path("manage/products/<int:pk>/edit/", admin_views.product_admin_edit, name="admin_edit"),
    path("manage/products/<int:pk>/delete/", admin_views.product_admin_delete, name="admin_delete"),
    path("manage/categories/", admin_views.category_admin_list, name="admin_categories"),
    path("manage/categories/add/", admin_views.category_admin_create, name="admin_category_create"),
    path("manage/categories/<int:pk>/edit/", admin_views.category_admin_edit, name="admin_category_edit"),
    path("manage/categories/<int:pk>/delete/", admin_views.category_admin_delete, name="admin_category_delete"),
    path("manage/orders/", admin_views.order_admin_list, name="admin_orders"),
    path("manage/orders/<int:pk>/status/", admin_views.order_admin_update_status, name="admin_order_status"),
    path("manage/reviews/", admin_views.review_admin_list, name="admin_reviews"),
    path("manage/reviews/<int:pk>/delete/", admin_views.review_admin_delete, name="admin_review_delete"),
]

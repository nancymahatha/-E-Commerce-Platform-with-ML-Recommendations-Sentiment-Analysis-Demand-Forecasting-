"""In-site STORE ADMIN — full CRUD inside the website itself.

Why not just use Django's built-in /admin/?
    For a non-technical shop owner we want the management screens to look and
    feel like the rest of the shop (same header, colours, language toggle). So
    this module provides add / edit / delete screens served from our own
    templates, guarded by the same `staff_required` role check.

Everything here is staff/admin only. Shoppers never see these pages.
"""
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import staff_required
from .forms import CategoryForm, ProductForm
from .models import Category, Product


# --------------------------------------------------------------------------- #
# Hub
# --------------------------------------------------------------------------- #
@staff_required
def store_admin(request):
    """Landing page: quick counts + links into each management area."""
    ctx = {
        "counts": {
            "products": Product.objects.count(),
            "categories": Category.objects.count(),
        },
        "recent_products": Product.objects.order_by("-created_at")[:8],
    }
    return render(request, "store_admin/index.html", ctx)


# --------------------------------------------------------------------------- #
# PRODUCTS — list / create / update / delete
# --------------------------------------------------------------------------- #
@staff_required
def product_admin_list(request):
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    products = Product.objects.select_related("category").order_by("-created_at")
    if q:
        products = products.filter(name__icontains=q)
    if cat:
        products = products.filter(category__slug=cat)

    ctx = {
        "products": products,
        "categories": Category.objects.all(),
        "q": q,
        "cat": cat,
    }
    return render(request, "store_admin/product_list.html", ctx)


@staff_required
def product_admin_create(request):
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product “{product.name}” was added.")
            return redirect("products:admin_list")
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = ProductForm()
    return render(request, "store_admin/product_form.html",
                  {"form": form, "mode": "create"})


@staff_required
def product_admin_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product “{product.name}” was updated.")
            return redirect("products:admin_list")
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = ProductForm(instance=product)
    return render(request, "store_admin/product_form.html",
                  {"form": form, "mode": "edit", "product": product})


@staff_required
def product_admin_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        name = product.name
        product.delete()
        messages.success(request, f"Product “{name}” was deleted.")
        return redirect("products:admin_list")
    return render(request, "store_admin/confirm_delete.html",
                  {"obj": product, "kind": "product",
                   "cancel_url": "products:admin_list"})


# --------------------------------------------------------------------------- #
# CATEGORIES — list / create / update / delete
# --------------------------------------------------------------------------- #
@staff_required
def category_admin_list(request):
    return render(request, "store_admin/category_list.html",
                  {"categories": Category.objects.all()})


@staff_required
def category_admin_create(request):
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            c = form.save()
            messages.success(request, f"Category “{c.name}” was added.")
            return redirect("products:admin_categories")
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = CategoryForm()
    return render(request, "store_admin/category_form.html",
                  {"form": form, "mode": "create"})


@staff_required
def category_admin_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            c = form.save()
            messages.success(request, f"Category “{c.name}” was updated.")
            return redirect("products:admin_categories")
        messages.error(request, "Please fix the highlighted fields below.")
    else:
        form = CategoryForm(instance=category)
    return render(request, "store_admin/category_form.html",
                  {"form": form, "mode": "edit", "category": category})


@staff_required
def category_admin_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == "POST":
        name = category.name
        category.delete()   # products get category=NULL (on_delete=SET_NULL)
        messages.success(request, f"Category “{name}” was deleted.")
        return redirect("products:admin_categories")
    return render(request, "store_admin/confirm_delete.html",
                  {"obj": category, "kind": "category",
                   "cancel_url": "products:admin_categories"})


# --------------------------------------------------------------------------- #
# ORDERS — list + status update
# --------------------------------------------------------------------------- #
@staff_required
def order_admin_list(request):
    from orders.models import Order
    status = request.GET.get("status", "")
    orders = Order.objects.select_related("user").order_by("-created_at")
    if status:
        orders = orders.filter(status=status)
    return render(request, "store_admin/order_list.html", {
        "orders": orders,
        "status": status,
        "status_choices": Order.STATUS,
    })


@staff_required
def order_admin_update_status(request, pk):
    """Staff can move an order between Paid / Pending / Shipped."""
    from orders.models import Order
    order = get_object_or_404(Order, pk=pk)
    if request.method == "POST":
        new_status = request.POST.get("status", "")
        valid = {c[0] for c in Order.STATUS}
        if new_status in valid:
            order.status = new_status
            order.save(update_fields=["status"])
            messages.success(request, f"Order #{order.id} marked as {new_status}.")
    return redirect("products:admin_orders")


# --------------------------------------------------------------------------- #
# REVIEWS — list + delete (moderation)
# --------------------------------------------------------------------------- #
@staff_required
def review_admin_list(request):
    from reviews.models import Review
    mood = request.GET.get("mood", "")
    reviews = Review.objects.select_related("user", "product").order_by("-created_at")
    if mood:
        reviews = reviews.filter(sentiment_label=mood)
    return render(request, "store_admin/review_list.html", {
        "reviews": reviews,
        "mood": mood,
    })


@staff_required
def review_admin_delete(request, pk):
    from reviews.models import Review
    review = get_object_or_404(Review, pk=pk)
    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted.")
    return redirect("products:admin_reviews")

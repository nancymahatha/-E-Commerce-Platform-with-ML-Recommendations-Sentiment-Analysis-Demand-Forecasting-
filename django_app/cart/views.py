from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from core.decorators import post_only
from products.models import Product
from .models import Cart, CartItem


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def view_cart(request):
    cart = _get_cart(request.user)
    return render(request, "cart/cart.html", {"cart": cart})


@login_required
@post_only("products:shop")
def add_to_cart(request):
    product = get_object_or_404(Product, pk=request.POST.get("product_id"))
    qty = int(request.POST.get("quantity", 1))
    cart = _get_cart(request.user)
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += qty
    else:
        item.quantity = qty
    item.save()
    return redirect("cart:cart")


@login_required
@post_only("cart:cart")
def remove_item(request, item_id):
    CartItem.objects.filter(pk=item_id, cart__user=request.user).delete()
    return redirect("cart:cart")

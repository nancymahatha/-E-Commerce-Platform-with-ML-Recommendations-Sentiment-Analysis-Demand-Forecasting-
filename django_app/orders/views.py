from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from cart.models import Cart, CartItem
from core.decorators import post_only
from .models import Order, OrderItem


@login_required
@post_only("cart:cart")
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        items = list(cart.items.all())
    except Cart.DoesNotExist:
        items = []

    if not items:
        return redirect("cart:cart")

    order = Order.objects.create(user=request.user, total=0, status="paid")
    total = 0
    for ci in items:
        OrderItem.objects.create(
            order=order,
            product=ci.product,
            name=ci.product.name,
            price=ci.product.price,
            quantity=ci.quantity,
        )
        total += ci.product.price * ci.quantity
    order.total = total
    order.save()

    # empty the cart after a successful order
    cart.items.all().delete()

    return redirect("orders:detail", pk=order.pk)


@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "orders/order_history.html", {"orders": orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, "orders/order_detail.html", {"order": order})

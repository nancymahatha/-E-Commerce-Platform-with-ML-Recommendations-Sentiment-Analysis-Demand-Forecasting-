"""Admin configuration for shopping carts.

Carts are working data, but staff may occasionally need to look one up or
clear a stuck cart, so we keep them visible with search + inline items.
"""
from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    fields = ("product", "quantity")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "item_count")
    search_fields = ("user__username",)
    list_select_related = ("user",)
    inlines = [CartItemInline]

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("id", "cart", "product", "quantity")
    search_fields = ("product__name", "cart__user__username")
    list_select_related = ("cart", "product")

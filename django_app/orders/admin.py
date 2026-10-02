"""Admin configuration for orders.

Staff can view every order, update its status, and see the items inside each
order right on the same page (inline). Orders are read-mostly: we keep the
line items read-only so a price/name that was charged is never rewritten.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    fields = ("product", "name", "price", "quantity", "line_total")
    readonly_fields = ("product", "name", "price", "quantity", "line_total")
    can_delete = False

    @admin.display(description="Line total")
    def line_total(self, obj):
        if not obj or obj.pk is None:
            return "—"
        return f"NRS {obj.price * obj.quantity:,.2f}"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_nrs", "status", "item_count", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "id")
    date_hierarchy = "created_at"
    list_per_page = 30
    inlines = [OrderItemInline]
    list_select_related = ("user",)

    @admin.display(description="Total (NRS)", ordering="total")
    def total_nrs(self, obj):
        return f"NRS {obj.total:,.2f}"

    @admin.display(description="Items")
    def item_count(self, obj):
        return obj.items.count()


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "name", "price_nrs", "quantity")
    search_fields = ("name", "order__id")
    list_select_related = ("order",)

    @admin.display(description="Price (NRS)")
    def price_nrs(self, obj):
        return f"NRS {obj.price:,.2f}"

"""Admin configuration for the product catalogue.

Designed so a NON-TECHNICAL shop owner can manage everything from /admin/:
  * add / edit / delete categories and products
  * search by name, filter by category
  * edit several products inside a category on one page (inline)
  * a live colour swatch for each product's accent, and a stock sanity column
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product


class ProductInline(admin.TabularInline):
    """Edit a category's products without leaving the category page."""
    model = Product
    extra = 0
    fields = ("name", "price", "stock", "demand_sku", "accent")
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "product_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductInline]

    @admin.display(description="Products")
    def product_count(self, obj):
        return obj.product_set.count()


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "colour_swatch", "category", "price_nrs", "stock", "rating", "demand_sku")
    list_filter = ("category", "created_at")
    search_fields = ("name", "description")
    list_editable = ("stock",)
    list_per_page = 30
    readonly_fields = ("created_at", "colour_preview")
    fieldsets = (
        ("Product details", {
            "fields": ("name", "category", "price", "description")
        }),
        ("Stock & pricing", {
            "fields": ("stock", "rating"),
            "description": "Set how many units you have and the average star rating (0–5).",
        }),
        ("Appearance", {
            "fields": ("accent", "colour_preview"),
            "description": "The colour used for the product placeholder image.",
        }),
        ("Advanced (linking)", {
            "fields": ("ml_item_id", "demand_sku", "created_at"),
            "classes": ("collapse",),
            "description": "These connect the product to the ML features. "
                           "Leave the defaults unless you know what you are doing.",
        }),
    )

    @admin.display(description="Price (NRS)")
    def price_nrs(self, obj):
        return f"NRS {obj.price:,.2f}"

    @admin.display(description="Colour")
    def colour_swatch(self, obj):
        return format_html(
            '<span style="display:inline-block;width:16px;height:16px;'
            'border-radius:4px;border:1px solid #ccc;background:{};"></span>',
            obj.accent,
        )

    @admin.display(description="Preview")
    def colour_preview(self, obj):
        if not obj or not obj.accent:
            return "—"
        return format_html(
            '<span style="display:inline-block;width:60px;height:24px;'
            'border-radius:6px;border:1px solid #ccc;background:{0};"></span>'
            '<span style="margin-left:8px;color:#666;">{0}</span>',
            obj.accent,
        )

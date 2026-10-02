"""Product catalog models.

Note on `ml_item_id`: it links each store product to an item id in the
recommendation dataset (Retailrocket). When we ask the ML service
"recommend for item X", it returns similar dataset item ids; we then look up
our Products whose ml_item_id matches. This is the bridge between the trained
recommender and our own shop inventory.
"""
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    ml_item_id = models.IntegerField(unique=True, help_text="id in the recommendation dataset")
    name = models.CharField(max_length=160)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)   # NRS
    description = models.TextField(blank=True)
    rating = models.FloatField(default=0.0)                        # average user rating
    stock = models.PositiveIntegerField(default=0)
    # links this product to the demand-forecasting dataset's abstract SKU (1-50)
    # so the admin dashboard can forecast demand for a REAL catalogue product.
    demand_sku = models.PositiveSmallIntegerField(default=1, help_text="demand SKU id (1-50)")
    # a soft color used for the gradient placeholder image (no external assets)
    accent = models.CharField(max_length=7, default="#d8c3b3")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

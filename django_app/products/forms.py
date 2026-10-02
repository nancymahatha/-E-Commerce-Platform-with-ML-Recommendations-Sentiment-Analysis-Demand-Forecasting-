"""Forms for the in-site store admin (staff-facing CRUD).

These are plain Django ModelForms with friendly labels + help text so a
non-technical shop owner can add/edit products without seeing Django jargon.
"""
from django import forms

from .models import Category, Product


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "slug"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Skincare"}),
            "slug": forms.TextInput(attrs={"placeholder": "e.g. skincare"}),
        }
        labels = {
            "name": "Category name",
            "slug": "Short code (URL)",
        }
        help_texts = {
            "name": "The name customers see, e.g. Skincare.",
            "slug": "Lower-case, no spaces. Used in the web address.",
        }


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name", "category", "price", "description",
            "stock", "rating", "accent", "demand_sku", "ml_item_id",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Hydrating Face Cream"}),
            "description": forms.Textarea(attrs={"rows": 3,
                                                 "placeholder": "Short description customers will read."}),
            "accent": forms.TextInput(attrs={"type": "color"}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "rating": forms.NumberInput(attrs={"step": "0.1", "min": "0", "max": "5"}),
        }
        labels = {
            "name": "Product name",
            "category": "Category",
            "price": "Price (NRS)",
            "description": "Description",
            "stock": "Stock (units available)",
            "rating": "Average rating (0–5)",
            "accent": "Card colour",
            "demand_sku": "Forecast link (1–50)",
            "ml_item_id": "Recommendation id",
        }
        help_texts = {
            "description": "Shown on the product page.",
            "stock": "How many units you currently have.",
            "rating": "Leave 0 if there are no reviews yet.",
            "accent": "Colour used for the product card placeholder.",
            "demand_sku": "Ties this product to the demand-forecast engine. Leave as is unless told otherwise.",
            "ml_item_id": "Ties this product to the similar-products engine. Must be unique.",
        }

    def clean_price(self):
        price = self.cleaned_data["price"]
        if price is not None and price < 0:
            raise forms.ValidationError("Price cannot be negative.")
        return price

    def clean_rating(self):
        rating = self.cleaned_data.get("rating") or 0
        if not (0 <= rating <= 5):
            raise forms.ValidationError("Rating must be between 0 and 5.")
        return rating

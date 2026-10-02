from django.conf import settings
from django.db import models
from products.models import Product


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()                 # 1-5 stars
    text = models.TextField()
    # True when this user actually ordered the product (checked at submit time).
    # Reviews from non-buyers are still allowed but carry no "verified" badge.
    verified_purchase = models.BooleanField(default=False)
    # filled by the ML service's /sentiment endpoint when the review is submitted
    sentiment_label = models.CharField(max_length=20, blank=True)        # positive/neutral/negative
    sentiment_confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        # one review per user per product
        constraints = [
            models.UniqueConstraint(fields=["product", "user"],
                                    name="one_review_per_user_per_product"),
        ]

    def __str__(self):
        return f"{self.user} -> {self.product} ({self.rating}★)"

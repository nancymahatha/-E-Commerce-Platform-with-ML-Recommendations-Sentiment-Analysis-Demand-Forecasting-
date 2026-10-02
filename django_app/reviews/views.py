"""Submit a review.

Two things happen here:

1. TRUST -- we check whether the reviewer actually bought the product. If they
   did, the review is marked `verified_purchase` and gets a badge in the UI.
   Non-buyers may still review, but their review is shown as unverified (the
   same approach Amazon uses). A user gets ONE review per product.

2. ML -- the review text is sent to the FastAPI /sentiment endpoint so we can
   store a sentiment label + confidence and render a coloured badge later.
"""
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect

from core.decorators import post_only
from core.ml_client import analyze_sentiment
from orders.models import OrderItem
from products.models import Product
from .models import Review


def user_bought_product(user, product):
    """True if this user has an order containing the product."""
    if not user.is_authenticated:
        return False
    return OrderItem.objects.filter(order__user=user, product=product).exists()


@login_required
@post_only("products:shop")
def add_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    try:
        rating = int(request.POST.get("rating", 0) or 0)
    except (TypeError, ValueError):
        rating = 0
    text = request.POST.get("text", "").strip()

    # ignore malformed submissions rather than storing junk
    if not text or not (1 <= rating <= 5):
        return redirect("products:product_detail", pk=product.pk)

    # --- trust: did this user actually buy this product? ----------------------
    verified = user_bought_product(request.user, product)

    # --- ML: classify the sentiment of the review text ------------------------
    sentiment = analyze_sentiment(text)
    if sentiment:
        label = sentiment.get("label", "")
        confidence = float(sentiment.get("confidence", 0.0))
    else:
        # graceful fallback: derive a label from the star rating if ML is down
        label = "positive" if rating >= 4 else ("neutral" if rating == 3 else "negative")
        confidence = 0.0

    # --- one review per user per product: update in place if it already exists --
    Review.objects.update_or_create(
        product=product,
        user=request.user,
        defaults={
            "rating": rating,
            "text": text,
            "verified_purchase": verified,
            "sentiment_label": label,
            "sentiment_confidence": confidence,
        },
    )
    return redirect("products:product_detail", pk=product.pk)

"""Product views: catalog list + detail page.

The detail page is where TWO ML features meet the user:
  1. "You may also like"  -> calls FastAPI /recommend (item-based CF).
  2. Reviews with sentiment badges -> each review's sentiment was computed by
     FastAPI /sentiment when it was submitted (see reviews.views.add_review).
"""
from django.shortcuts import get_object_or_404, render

from core.ml_client import _co_view_counts, recommend_by_item, recommend_popular
from .models import Category, Product


def product_list(request):
    q = request.GET.get("q", "")
    cat = request.GET.get("category", "")
    products = Product.objects.all()
    if q:
        products = products.filter(name__icontains=q)
    if cat:
        products = products.filter(category__slug=cat)
    categories = Category.objects.all()

    # Popular items (fallback recommendations) for the sidebar / empty states.
    popular = recommend_popular(k=8)
    popular_ids = [p["itemid"] for p in popular.get("items", [])] if popular else []
    popular_products = list(Product.objects.filter(ml_item_id__in=popular_ids))
    # keep the ML-ranked order
    by_id = {p.ml_item_id: p for p in popular_products}
    popular_products = [by_id[i] for i in popular_ids if i in by_id]

    ctx = {
        "products": products,
        "categories": categories,
        "popular_products": popular_products,
        "q": q,
    }
    return render(request, "products/product_list.html", ctx)


def home(request):
    """Landing page: category showcase, popular products, benefits and reviews."""
    categories = Category.objects.all()

    popular = recommend_popular(k=8)
    popular_ids = [p["itemid"] for p in popular.get("items", [])] if popular else []
    popular_products = list(Product.objects.filter(ml_item_id__in=popular_ids))
    by_id = {p.ml_item_id: p for p in popular_products}
    popular_products = [by_id[i] for i in popular_ids if i in by_id]

    # A few genuine positive reviews to feature on the landing page.
    testimonials = []
    try:
        from reviews.models import Review
        testimonials = list(
            Review.objects.filter(sentiment_label="positive")
            .select_related("user")
            .order_by("-rating", "-created_at")[:3]
        )
    except Exception:
        testimonials = []

    ctx = {
        "categories": categories,
        "popular_products": popular_products,
        "testimonials": testimonials,
    }
    return render(request, "home.html", ctx)


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # 1) recommendations: ask the ML service for items similar to this one.
    #
    #    We request a LARGER candidate pool (k=20) than we display (4), then
    #    re-rank that pool. Why: the model's cosine score is noisy when an item
    #    has a thin audience (some products were viewed by only 1-14 shoppers),
    #    so a weak neighbour can out-rank a strong one at the head of the list.
    #
    #    The re-rank blends two signals the model already gives us:
    #      * co-viewers  = how many shoppers viewed BOTH products (real evidence)
    #      * cosine      = the model's similarity score
    #    plus a small nudge toward the same category (a normal shop behaviour).
    #
    #    This is a RE-RANK of the model's own output -- the trained similarity
    #    matrix and the model itself are never modified.
    recs = recommend_by_item(product.ml_item_id, k=20)
    recommended = []
    if recs:
        cand = recs.get("items", [])
        rec_ids = [r["itemid"] for r in cand]
        scores = {r["itemid"]: (r.get("score") or 0.0) for r in cand}
        rec_products = Product.objects.filter(ml_item_id__in=rec_ids)
        by_id = {p.ml_item_id: p for p in rec_products}
        keep = [i for i in rec_ids if i in by_id]

        if keep:
            import numpy as np

            overlap = _co_view_counts(product.ml_item_id, keep)

            ov = np.array([overlap.get(i, 0) for i in keep], dtype=float)
            cs = np.array([scores.get(i, 0.0) for i in keep], dtype=float)
            # min-max normalise each signal so the weights below are comparable
            ov_n = ov / ov.max() if ov.max() > 0 else ov
            cs_n = (cs - cs.min()) / (cs.max() - cs.min()) if cs.max() > cs.min() else cs * 0.0
            cat_bonus = np.array([
                0.25 if by_id[i].category_id == product.category_id else 0.0
                for i in keep
            ])

            blended = 0.5 * ov_n + 0.4 * cs_n + cat_bonus
            order = [keep[j] for j in np.argsort(blended)[::-1]]
            recommended = [by_id[i] for i in order][:4]

    # popular items (used as a fallback if no ML neighbours map to our catalog)
    popular = recommend_popular(k=8)
    popular_ids = [p["itemid"] for p in popular.get("items", [])] if popular else []
    popular_products = list(Product.objects.filter(ml_item_id__in=popular_ids))
    by_pop = {p.ml_item_id: p for p in popular_products}
    popular_products = [by_pop[i] for i in popular_ids if i in by_pop]

    # 2) reviews for this product (sentiment already stored on each review)
    from reviews.models import Review
    from reviews.views import user_bought_product
    reviews = product.reviews.all().order_by("-created_at")

    # trust signals for the review form
    bought = user_bought_product(request.user, product)
    has_reviewed = (request.user.is_authenticated and
                    product.reviews.filter(user=request.user).exists())

    # fallback: if the ML service returned no mappable neighbours, show popular items
    if not recommended and popular_products:
        recommended = popular_products[:4]

    # how many of the shown reviews are from verified buyers
    verified_count = sum(1 for r in reviews if r.verified_purchase)

    # ---- staff-only: at-a-glance sentiment gist for this product ----
    # The ML sentiment label is an internal triage signal, not shopper-facing.
    # We compute the rollup ONLY for staff/admin so the counts never leak.
    sentiment_summary = None
    profile = getattr(request.user, "profile", None)
    if request.user.is_authenticated and profile and profile.is_staff_role():
        labels = [r.sentiment_label for r in reviews if r.sentiment_label]
        confs = [r.sentiment_confidence for r in reviews if r.sentiment_label]
        if labels:
            sentiment_summary = {
                "positive": labels.count("positive"),
                "neutral": labels.count("neutral"),
                "negative": labels.count("negative"),
                "total": len(labels),
                "avg_confidence": (sum(confs) / len(confs)) if confs else 0.0,
            }

    ctx = {
        "product": product,
        "recommended": recommended,
        "reviews": reviews,
        "bought": bought,
        "has_reviewed": has_reviewed,
        "verified_count": verified_count,
        "sentiment_summary": sentiment_summary,
    }
    return render(request, "products/product_detail.html", ctx)

"""Custom template filters: NRS currency formatting and star ratings."""
import os

from django import template
from django.conf import settings
from django.contrib.staticfiles.finders import find

from core.translations import NE_TABLES

register = template.Library()


@register.filter
def nrs(value):
    """Format a number as Nepali Rupees, e.g. 1299 -> 'NRS 1,299'."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return value
    if v == int(v):
        return f"NRS {int(v):,}"
    return f"NRS {v:,.2f}"


@register.filter
def stars(rating):
    """Return the integer number of full stars for a rating (0-5)."""
    try:
        return int(round(float(rating)))
    except (TypeError, ValueError):
        return 0


@register.filter
def sentiment_color(label):
    return {
        "positive": "var(--pos)",
        "neutral": "var(--neu)",
        "negative": "var(--neg)",
    }.get(str(label).lower(), "var(--muted)")


@register.simple_tag(takes_context=True)
def trn(context, group, value, default=""):
    """Translate a value that lives in the DATABASE (not in the EN/NE dicts).

    Categories, sentiment labels, order statuses and user roles are stored in
    English, so they can't be translated via {{ STR.* }}. This tag looks them up
    in core.translations.NE_TABLES, and only when the active language is Nepali.

    Product NAMES are intentionally never passed through here — they stay English.

    Usage:  {% trn 'category' p.category.slug default=p.category.name %}
    """
    fallback = default if default not in (None, "") else ("" if value is None else str(value))
    try:
        lang = str(context.get("lang", "en")).lower()
    except Exception:
        lang = "en"
    if lang != "ne":
        return fallback
    key = "" if value is None else str(value).lower()
    return NE_TABLES.get(group, {}).get(key, fallback)


def _category_pool(slug):
    """Which numbered images exist for a category: <slug>-1.jpg ... <slug>-N.jpg.

    Read from disk every call (no caching) so newly dropped-in photos are
    picked up without a server restart.
    """
    nums = []
    for base in getattr(settings, "STATICFILES_DIRS", []) or []:
        d = os.path.join(str(base), "img", "products")
        if os.path.isdir(d):
            for i in range(1, 25):
                if os.path.exists(os.path.join(d, f"{slug}-{i}.jpg")):
                    nums.append(i)
            if nums:
                return nums
    # fallback if STATICFILES_DIRS isn't configured
    for i in range(1, 25):
        if find(f"img/products/{slug}-{i}.jpg"):
            nums.append(i)
    return nums


@register.filter
def product_img(product):
    """Pick an image for this product.

    1. Per-category pool  -> img/products/<category>-1..N.jpg, spread across
       products by id so a category with several photos (haircare-1..6.jpg)
       shows all of them instead of repeating one.
    2. Product-type image -> img/products/<noun>.jpg (noun = 2nd word of name).
    3. None -> template falls back to the soft gradient placeholder.
    """
    slug = None
    try:
        if product.category_id and product.category:
            slug = product.category.slug
    except Exception:
        slug = None

    if slug:
        pool = _category_pool(slug)
        if pool:
            idx = (product.pk or 0) % len(pool)
            return f"img/products/{slug}-{pool[idx]}.jpg"

    parts = product.name.split()
    noun = parts[1].lower() if len(parts) >= 2 else "default"
    rel = f"img/products/{noun}.jpg"
    return rel if find(rel) else None

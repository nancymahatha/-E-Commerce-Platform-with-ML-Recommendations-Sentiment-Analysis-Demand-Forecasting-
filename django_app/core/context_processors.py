"""
Context processor: makes language, theme and translated strings available in
EVERY template. Called automatically on each request (wired in settings.TEMPLATES).
"""
from .translations import TRANSLATIONS, DEFAULT_LANG


def shop(request):
    # Language: read from session (set by accounts.views.set_language), default EN.
    lang = request.session.get("lang") or DEFAULT_LANG
    if lang not in TRANSLATIONS:
        lang = DEFAULT_LANG

    # Theme: single nude/classic palette (dashain mode removed).
    theme = request.session.get("theme") or "nude"

    data = {
        "lang": lang,
        "theme": theme,
        "STR": TRANSLATIONS[lang],
        "LANGS": [("en", "EN"), ("ne", "नेपाली")],
    }

    # Auth-aware extras for the nav bar.
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        data["user_role"] = profile.role if profile else "customer"
        data["is_staff_role"] = bool(profile and profile.is_staff_role())
        from cart.models import Cart
        try:
            data["cart_count"] = Cart.objects.get(user=request.user).count()
        except Cart.DoesNotExist:
            data["cart_count"] = 0
    else:
        data["user_role"] = None
        data["is_staff_role"] = False
        data["cart_count"] = 0

    return data

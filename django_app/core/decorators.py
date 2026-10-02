"""Shared view decorators.

`post_only` is a friendlier sibling of Django's `require_POST`.

Why not just `@require_POST`?
    `@require_POST` returns a bare HTTP 405 whenever a browser sends a GET.
    That is *correct* HTTP, but the browser renders it as the raw
    "This page isn't working — HTTP ERROR 405" notice, which looks like a
    crash. Real users hit this by refreshing a page they just submitted,
    pressing Back onto a form URL, or opening a bookmarked action URL.

`post_only` keeps the endpoint POST-only in spirit, but for a GET it simply
redirects the visitor to a sensible GET page (the cart, the shop, or a
custom `redirect_to`) instead of dead-ending them.
"""
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect


def post_only(redirect_to="products:shop", note=None):
    """Allow only POST; on other methods, redirect instead of returning 405.

    Usage:
        @login_required
        @post_only("cart:cart")
        def add_to_cart(request): ...
    """

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method == "POST":
                return view(request, *args, **kwargs)
            # Any non-POST (GET / HEAD / OPTIONS): bounce them somewhere useful.
            if request.method in ("GET", "HEAD") and note:
                messages.info(request, note)
            return redirect(redirect_to)

        return wrapper

    return decorator

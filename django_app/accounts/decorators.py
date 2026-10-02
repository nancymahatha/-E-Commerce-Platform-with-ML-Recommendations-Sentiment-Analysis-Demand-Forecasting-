"""Authorization decorator: only users with a staff/admin profile may pass."""
from functools import wraps

from django.shortcuts import redirect
from django.contrib.auth.views import redirect_to_login


def staff_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not getattr(request.user, "profile", None) or not request.user.profile.is_staff_role():
            return redirect("accounts:staff_denied")
        return view_func(request, *args, **kwargs)

    return _wrapped

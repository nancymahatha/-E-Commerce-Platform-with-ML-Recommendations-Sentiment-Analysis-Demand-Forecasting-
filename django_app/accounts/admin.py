"""Admin configuration for user profiles.

Lets staff switch a user's role (customer / staff / admin) from /admin/.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import UserProfile

_ROLE_STYLE = {
    "admin": ("#f3e9df", "#9c6f52"),
    "staff": ("#efe3d6", "#b08968"),
    "customer": ("#f3efe6", "#6b5b4f"),
}


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role_badge", "phone")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email", "phone")
    list_select_related = ("user",)

    @admin.display(description="Role", ordering="role")
    def role_badge(self, obj):
        bg, fg = _ROLE_STYLE.get(obj.role, ("#eee", "#333"))
        return format_html(
            '<span style="background:{0};color:{1};padding:2px 8px;border-radius:10px;'
            'font-size:12px;font-weight:600;">{2}</span>',
            bg, fg, obj.role.title(),
        )

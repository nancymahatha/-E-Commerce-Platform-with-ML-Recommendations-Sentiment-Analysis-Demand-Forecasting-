"""Admin configuration for customer reviews.

Staff can read, moderate and delete reviews here. The review's automated
mood label (positive / neutral / negative) and the model's CONFIDENCE SCORE
are shown as read-only columns so they cannot be edited by hand.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import Review

# small colour chips so a non-technical reader can scan the mood at a glance
_MOOD_STYLE = {
    "positive": ("#eaf3de", "#27500a"),
    "neutral": ("#f3efe6", "#6b5b4f"),
    "negative": ("#fbe6e6", "#a32d2d"),
}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "stars", "mood_badge", "confidence_pct",
                    "verified_purchase", "created_at")
    list_filter = ("sentiment_label", "verified_purchase", "rating", "created_at")
    search_fields = ("text", "user__username", "product__name")
    date_hierarchy = "created_at"
    list_per_page = 30
    list_select_related = ("user", "product")
    readonly_fields = ("sentiment_label", "sentiment_confidence", "created_at")
    fieldsets = (
        ("Review", {
            "fields": ("product", "user", "rating", "text", "verified_purchase"),
        }),
        ("Automatic mood analysis (read-only)", {
            "fields": ("sentiment_label", "sentiment_confidence"),
            "description": "Filled in automatically when the customer submits the "
                           "review. Confidence is how sure the system is (0–1).",
        }),
        ("Meta", {
            "fields": ("created_at",),
        }),
    )

    @admin.display(description="Rating", ordering="rating")
    def stars(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @admin.display(description="Mood", ordering="sentiment_label")
    def mood_badge(self, obj):
        label = obj.sentiment_label or "—"
        bg, fg = _MOOD_STYLE.get(label, ("#eee", "#333"))
        return format_html(
            '<span style="background:{0};color:{1};padding:2px 8px;border-radius:10px;'
            'font-size:12px;font-weight:600;">{2}</span>',
            bg, fg, label.title(),
        )

    @admin.display(description="Confidence", ordering="sentiment_confidence")
    def confidence_pct(self, obj):
        # keep the score, but show it as a friendly percentage
        return f"{round(obj.sentiment_confidence * 100)}%"

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render

from core.decorators import post_only
from core.ml_client import forecast_demand, ml_health
from .decorators import staff_required
from .forms import RegistrationForm
from .models import UserProfile


# --- auth views (Django built-ins, themed templates) ---
class ThemedLoginView(LoginView):
    template_name = "accounts/login.html"


class ThemedLogoutView(LogoutView):
    next_page = "/"

    # Django 5+ restricts LogoutView to POST only. We keep POST as the real
    # logout action (that's what the nav form sends) but ALSO allow GET so that
    # an old link / bookmark / refresh lands somewhere sensible instead of
    # showing the raw "HTTP ERROR 405" page.
    http_method_names = ["get", "post", "options"]

    def get(self, request, *args, **kwargs):
        """GET must NOT log the user out (safer), but it should not 405 either.
        Send the visitor home."""
        return redirect(self.next_page)


def register(request):
    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # the post_save signal already created a profile; set its role
            profile = UserProfile.objects.get(user=user)
            role = form.cleaned_data["role"]
            profile.role = role
            profile.save()
            # Registering as "admin" also grants access to the Django admin site
            # (otherwise role=admin could open the dashboard but never /admin/).
            if role == "admin":
                user.is_staff = True
                user.is_superuser = True
                user.save(update_fields=["is_staff", "is_superuser"])
            login(request, user)
            return redirect("products:shop")
    else:
        form = RegistrationForm()
    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    profile = request.user.profile
    return render(request, "accounts/profile.html", {"profile": profile})


def staff_denied(request):
    return render(request, "accounts/staff_denied.html", status=403)


@staff_required
def demand_dashboard(request):
    """Staff-only ML analytics console.

    Surfaces the three ML capabilities that matter to an operator:
      * demand forecast  -> FastAPI /demand (XGBoost) for a chosen store+product
      * model health      -> FastAPI /health (status + evaluation metrics)
      * review sentiment   -> stored labels from FastAPI /sentiment (admin insight)

    The demand model is trained on a store-demand dataset whose items are abstract
    SKU ids 1-50. Each catalogue product carries a `demand_sku` (1-50) so we can
    forecast for a REAL product; we also show the site's OWN sales history so the
    forecast is clearly grounded in local data.
    """
    from products.models import Product
    from reviews.models import Review
    from orders.models import Order, OrderItem
    from core.charts import line_chart, bar_chart, donut_chart
    from datetime import date, timedelta
    from django.db.models import Count, Sum
    from django.db.models.functions import TruncDate, TruncWeek

    # The demand model is trained on abstract SKUs 1..50. Many catalogue
    # products share a SKU, so we let staff pick a REAL product from a dropdown
    # and we forecast on THAT product's demand_sku. Crucially we keep the exact
    # chosen product object (by pk) so the result headline always matches what
    # was picked — we never re-derive the product from the SKU (which would show
    # a different product that happens to share the same SKU).
    product_options = list(Product.objects.order_by("name"))
    # dropdown shows every product; the value is the product's primary key
    product_choices = [(p.pk, p.name) for p in product_options]

    def product_for_pk(pk):
        try:
            return Product.objects.filter(pk=int(pk)).first()
        except (TypeError, ValueError):
            return None

    store = request.GET.get("store", "1")
    product_pk = request.GET.get("product", "")
    result = None
    result_product = None
    result_sku = None
    line_svg = ""
    forecast_basis = None
    if request.GET.get("run"):
        try:
            s = int(store)
        except (TypeError, ValueError):
            s = 1
        # resolve the chosen product first, then forecast on ITS demand_sku
        chosen = product_for_pk(product_pk) if product_pk else None
        if chosen is None:
            chosen = product_options[0] if product_options else None
        result_product = chosen
        i = int(chosen.demand_sku) if chosen is not None else 1
        result_sku = i
        result = forecast_demand(s, i, 30)
        if result:
            start = date.today()
            labels = [(start + timedelta(days=d)).strftime("%b %d") for d in range(30)]
            line_svg = line_chart(result["predicted_daily_units"], labels=labels)

            # --- show the BASIS of the forecast (so staff can see WHY) ---
            from core.ml_client import demand_history
            hist = demand_history(s, i)
            daily = result.get("predicted_daily_units", []) or []
            if hist:
                past = hist.get("sales", [])
                forecast_basis = {
                    "past": past,                     # real last-N-days units the model started from
                    "past_labels": hist.get("labels", []),
                    "history_days": len(past),
                    "last_date": hist.get("last_date"),
                    "avg_past": round(sum(past) / len(past), 1) if past else 0,
                    "peak_past": max(past) if past else 0,
                    "low_past": min(past) if past else 0,
                    "forecast_total": result.get("predicted_total_units"),
                    "forecast_avg": round(sum(daily) / len(daily), 1) if daily else 0,
                    "trend": ("up" if daily and past and (sum(daily) / len(daily)) > (sum(past) / len(past))
                              else ("down" if daily and past else "flat")),
                    "weekend_effect": True,           # the model explicitly uses day-of-week
                }

    # ---- the site's OWN sales history (grounds demand in local data) ----
    sales_by_day = (OrderItem.objects
                    .annotate(d=TruncDate("order__created_at"))
                    .values("d")
                    .annotate(units=Sum("quantity"), revenue=Sum("price"))
                    .order_by("d"))
    sales_daily = [{"date": r["d"], "units": r["units"] or 0} for r in sales_by_day]
    total_units = sum(r["units"] for r in sales_daily)
    total_orders = Order.objects.count()
    days_span = 0
    if sales_daily:
        days_span = (sales_daily[-1]["date"] - sales_daily[0]["date"]).days + 1
    avg_per_day = round(total_units / days_span, 1) if days_span else 0

    # 30-day sparkline of actual daily units (real site sales)
    recent = sales_daily[-30:]
    if recent:
        labels = [r["date"].strftime("%b %d") for r in recent]
        sales_line_svg = line_chart([r["units"] for r in recent], labels=labels)
    else:
        sales_line_svg = ""

    # top-selling products (from real orders)
    top_sellers = (OrderItem.objects
                   .values("name")
                   .annotate(units=Sum("quantity"))
                   .order_by("-units")[:8])
    top_seller_pairs = [(r["name"][:12], r["units"]) for r in top_sellers]
    top_seller_svg = bar_chart(top_seller_pairs) if top_seller_pairs else ""

    # precomputed sample forecasts so the page is useful on first load.
    # each sample uses a real product; we forecast on that product's demand_sku.
    sample_products = product_options[:4]
    samples = []
    for p in sample_products:
        d = forecast_demand(1, int(p.demand_sku), 30)
        if d:
            samples.append({
                "store": 1, "item": int(p.demand_sku),
                "total": d["predicted_total_units"],
                "product": p,
                "start": d["start_date"], "end": d["end_date"],
            })
    bar_pairs = [
        ((sm["product"].name if sm["product"] else f"SKU {sm['item']}")[:12], sm["total"])
        for sm in samples
    ]
    bar_svg = bar_chart(bar_pairs) if bar_pairs else ""

    # live forecast-engine status (kept simple for non-technical staff)
    health = ml_health()
    health_cards = []
    if health and health.get("models"):
        m = health["models"]

        # Friendly names + one plain-English line about what each engine does.
        _LABELS = [
            ("recommendation", "Recommendations",
             "Suggests similar products shoppers may like."),
            ("sentiment", "Review mood",
             "Reads each review and labels how the customer felt."),
            ("demand", "Demand forecast",
             "Predicts how many units you will sell."),
        ]

        def _accuracy(bundle):
            """Turn a metrics dict into one readable accuracy line."""
            metrics = (bundle or {}).get("metrics") or {}
            if not metrics:
                return ""
            # pick the most meaningful metric for each model, whatever it's named
            for pref in ("accuracy", "precision@5", "rmse"):
                if pref in metrics:
                    v = metrics[pref]
                    label = {"accuracy": "accuracy", "precision@5": "accuracy",
                             "rmse": "typical error"}[pref]
                    return f"{label}: {v:.2f}" if isinstance(v, float) else f"{label}: {v}"
            k, v = next(iter(metrics.items()))
            return f"{k}: {v:.2f}" if isinstance(v, float) else f"{k}: {v}"

        for key, name, blurb in _LABELS:
            b = m.get(key) or {}
            acc = _accuracy(b)
            health_cards.append({
                "name": name,
                "type": blurb,
                "metric": acc,
                "ok": bool(b.get("loaded")),
            })

    # admin-only sentiment insight
    sent_counts = {"positive": 0, "neutral": 0, "negative": 0}
    for lab in Review.objects.values_list("sentiment_label", flat=True):
        if lab in sent_counts:
            sent_counts[lab] += 1
    donut_svg = donut_chart(sent_counts)
    negative_reviews = list(
        Review.objects.filter(sentiment_label="negative")
        .select_related("user", "product").order_by("-created_at")[:6]
    )

    # management overview so an admin can see everything at a glance
    from products.models import Category
    mgmt = {
        "products": Product.objects.count(),
        "categories": Category.objects.count(),
        "reviews": Review.objects.count(),
        "orders": total_orders,
        "users": get_user_model().objects.count(),
    }

    ctx = {
        "result": result,
        "result_product": result_product,
        "result_sku": result_sku,
        "line_svg": line_svg,
        "forecast_basis": forecast_basis,
        "store": store, "product_pk": product_pk,
        "product_choices": product_choices,
        "samples": samples,
        "bar_svg": bar_svg,
        "health": health,
        "health_cards": health_cards,
        "sent_counts": sent_counts,
        "donut_svg": donut_svg,
        "negative_reviews": negative_reviews,
        "mgmt": mgmt,
        # site-sales signals
        "sales_line_svg": sales_line_svg,
        "top_seller_svg": top_seller_svg,
        "sales_total_units": total_units,
        "sales_avg_per_day": avg_per_day,
        "sales_days": days_span,
        "sales_recent_days": len(recent),
    }
    return render(request, "accounts/demand_dashboard.html", ctx)


@staff_required
@post_only("accounts:demand_dashboard")
def moderate_review(request):
    """Staff-only moderation: delete a review flagged by the ML sentiment model."""
    rid = request.POST.get("review_id")
    if rid and str(rid).isdigit():
        from reviews.models import Review
        Review.objects.filter(pk=int(rid)).delete()
    return redirect("accounts:demand_dashboard")


# --- language + theme toggles (store choice in the session) ---
def set_language(request):
    lang = request.GET.get("lang", "en")
    request.session["lang"] = lang
    return redirect(request.GET.get("next", "/") or "/")


def set_theme(request):
    theme = request.GET.get("theme", "nude")
    request.session["theme"] = theme
    return redirect(request.GET.get("next", "/") or "/")

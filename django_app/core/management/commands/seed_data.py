"""Seed the website with realistic LOCAL data so all three ML features have
something real to work on:

  * ~20 demo customers          -> so orders/reviews have authors
  * Product.demand_sku (1-50)    -> maps each product to the demand model's SKU
  * ~260 orders spread over the last 8 months (with dates!)
                                 -> gives the site a REAL sales history
  * ~130 reviews (mixed text)    -> labelled by the REAL FastAPI /sentiment model
  * some cart items              -> interaction signal

Usage (from django_app/):
    python manage.py seed_data
    python manage.py seed_data --reset     # wipe seeded rows first

Sentiment labels are produced by calling the live ML service; if it is down the
command falls back to rating-derived labels and says so.
"""
import os
import random
from datetime import timedelta
from decimal import Decimal

import django
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from django.contrib.auth import get_user_model

from products.models import Product
from reviews.models import Review
from orders.models import Order, OrderItem
from cart.models import Cart, CartItem
from core.ml_client import analyze_sentiment

User = get_user_model()

# ---------------------------------------------------------------- demo people
FIRST = ["Aarati", "Bikash", "Chhaya", "Dipesh", "Elena", "Farhan", "Gita", "Hari",
         "Ishita", "Jeevan", "Kabita", "Laxmi", "Manish", "Nisha", "Ojas", "Pratima",
         "Ramesh", "Sita", "Tara", "Utsav", "Bina", "Sujan", "Rekha", "Anil"]
LAST = ["Sharma", "Thapa", "Gurung", "Rai", "Karki", "Adhikari", "Bista", "Magar",
        "Shrestha", "Joshi", "Poudel", "Basnet"]

# --------------------------------------------------------------- review texts
# Grouped so sentiment is unambiguous; the model still labels them itself.
POS = [
    "Absolutely love this, my skin feels amazing and it smells divine.",
    "Great quality and arrived quickly, will definitely buy again.",
    "This is my new favourite, gentle and effective. Highly recommend.",
    "Excellent product, works exactly as described and feels premium.",
    "So happy with this purchase, it made a real difference within a week.",
    "Beautiful packaging and the product itself is wonderful value for money.",
    "Really impressed, it is light, absorbs fast and does not feel greasy.",
    "Perfect for daily use, my skin looks brighter and healthier now.",
    "Fantastic, exceeded my expectations and the delivery was fast.",
    "I recommend this to all my friends, worth every rupee.",
]
NEU = [
    "It is okay, nothing special, but does the job I suppose.",
    "Decent product, average quality for the price, neither good nor bad.",
    "Fine, the colour was a little different from the photos though.",
    "It works but I expected a bit more, it is just average overall.",
    "Not bad, not great, probably would try something else next time.",
    "The product is alright, delivery took longer than expected.",
]
NEG = [
    "Very disappointed, it broke after one use and the quality feels cheap.",
    "Terrible product, caused irritation and I want a refund immediately.",
    "Bad quality, arrived damaged and nothing like the description shown.",
    "Waste of money, the smell is awful and it did nothing for my skin.",
    "Not happy at all, packaging leaked and the product seems expired.",
    "Poor quality and poor service, would not recommend this to anyone.",
    "It stopped working after a few days, completely useless purchase.",
]

CATEGORY_HINT = {}


class Command(BaseCommand):
    help = "Seed realistic local data (users, orders, reviews, carts) for the ML features."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true",
                            help="delete previously seeded orders/reviews/carts first")
        parser.add_argument("--customers", type=int, default=20)
        parser.add_argument("--orders", type=int, default=260)
        parser.add_argument("--reviews", type=int, default=130)

    @transaction.atomic
    def handle(self, *args, **opts):
        random.seed(42)
        products = list(Product.objects.all())
        if not products:
            self.stderr.write("No products found - run `python seed.py` first.")
            return

        if opts["reset"]:
            OrderItem.objects.all().delete()
            Order.objects.all().delete()
            Review.objects.all().delete()
            CartItem.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared existing orders/reviews/carts."))

        # ---- 1. demand_sku mapping: spread SKUs 1..50 across the catalogue ----
        for i, p in enumerate(products):
            sku = (i % 50) + 1
            if p.demand_sku != sku:
                p.demand_sku = sku
                p.save(update_fields=["demand_sku"])
        self.stdout.write(f"Assigned demand_sku 1-50 across {len(products)} products.")

        # ---- 2. customers ----
        customers = []
        for n in range(opts["customers"]):
            fn, ln = random.choice(FIRST), random.choice(LAST)
            username = f"{fn.lower()}{n+1}"
            user, created = User.objects.get_or_create(
                username=username, defaults={"email": f"{username}@demo.com"})
            if created:
                user.set_password("DemoPass1234")
                user.save()
            # make sure a profile exists with role=customer
            from accounts.models import UserProfile
            prof, _ = UserProfile.objects.get_or_create(user=user)
            if prof.role != "customer":
                prof.role = "customer"
                prof.save()
            customers.append(user)
        self.stdout.write(f"Customers ready: {len(customers)} (password DemoPass1234)")

        # ---- 3. orders spread over the last ~8 months ----
        # concentrate on a "popular" subset so top-sellers and per-product
        # history look realistic (a long tail of 1-sale items looks fake).
        order_pool = random.sample(products, min(120, len(products))) * 2 + products[:80]
        now = timezone.now()
        statuses = ["paid", "shipped", "pending"]
        made_orders = 0
        made_items = 0
        for _ in range(opts["orders"]):
            user = random.choice(customers)
            days_ago = random.randint(0, 240)
            created = now - timedelta(days=days_ago,
                                      hours=random.randint(0, 23),
                                      minutes=random.randint(0, 59))
            order = Order.objects.create(
                user=user, total=0, status=random.choices(statuses, [6, 3, 1])[0])
            # backdate it (auto_now_add would otherwise stamp "now")
            Order.objects.filter(pk=order.pk).update(created_at=created)

            total = Decimal("0")
            for prod in random.sample(order_pool, random.randint(1, 4)):
                qty = random.randint(1, 3)
                OrderItem.objects.create(
                    order=order, product=prod, name=prod.name,
                    price=prod.price, quantity=qty)
                total += prod.price * qty
                made_items += 1
            Order.objects.filter(pk=order.pk).update(total=total)
            made_orders += 1
        self.stdout.write(f"Orders created: {made_orders} ({made_items} line items, "
                          f"spread over the last 240 days)")

        # ---- 4. reviews labelled by the REAL ML model ----
        # Concentrate reviews on a smaller "popular" set so individual product
        # pages actually show SEVERAL reviews (looks real, not 1-per-product).
        popular = random.sample(products, min(60, len(products)))
        buckets = [("pos", POS, (4, 5)), ("neu", NEU, (3, 3)), ("neg", NEG, (1, 2))]
        model_hits, fallbacks = 0, 0
        texts_by_label = {"positive": 0, "neutral": 0, "negative": 0}

        # build a weighted product list: popular items appear ~3x more often
        weighted = popular * 3 + random.sample(products, min(200, len(products)))

        for _ in range(opts["reviews"]):
            prod = random.choice(weighted)
            kind, pool, ratings = random.choices(buckets, [55, 20, 25])[0]
            text = random.choice(pool)
            rating = random.randint(*ratings)
            user = random.choice(customers)

            sent = analyze_sentiment(text)
            if sent:
                label = sent.get("label", "")
                conf = float(sent.get("confidence", 0.0))
                model_hits += 1
            else:
                label = "positive" if rating >= 4 else ("neutral" if rating == 3 else "negative")
                conf = 0.0
                fallbacks += 1

            r = Review.objects.create(
                product=prod, user=user, rating=rating, text=text,
                sentiment_label=label, sentiment_confidence=conf)
            # backdate
            Review.objects.filter(pk=r.pk).update(
                created_at=now - timedelta(days=random.randint(0, 200)))
            if label in texts_by_label:
                texts_by_label[label] += 1

        self.stdout.write(
            f"Reviews created: {opts['reviews']} across {len(set(weighted))} products  "
            f"(model-labelled: {model_hits}, fallback: {fallbacks})")
        self.stdout.write(f"  sentiment spread: {texts_by_label}")

        # ---- 5. a little cart activity ----
        made_cart = 0
        for user in random.sample(customers, min(8, len(customers))):
            cart, _ = Cart.objects.get_or_create(user=user)
            for prod in random.sample(products, random.randint(1, 3)):
                CartItem.objects.get_or_create(cart=cart, product=prod,
                                               defaults={"quantity": random.randint(1, 2)})
                made_cart += 1
        self.stdout.write(f"Cart items created: {made_cart}")

        # ---- summary ----
        self.stdout.write(self.style.SUCCESS(
            f"\nDONE. products={Product.objects.count()} users={User.objects.count()} "
            f"orders={Order.objects.count()} reviews={Review.objects.count()} "
            f"cart_items={CartItem.objects.count()}"))

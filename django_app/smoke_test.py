"""
End-to-end smoke test of auth + authorization + ML integration using Django's
test Client (no browser, no passwords in shell history). Run: python smoke_test.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User
from products.models import Product
from orders.models import Order
from reviews.models import Review

PW = "TestPass1234"
c = Client(SERVER_NAME="127.0.0.1")


def reg(username, role):
    r = c.post("/accounts/register/", {
        "username": username, "email": f"{username}@demo.com",
        "password1": PW, "password2": PW, "role": role,
    })
    print(f"  register {username} ({role}): {r.status_code} -> {r.get('Location')}")


print("[1] public home"); print(" ", c.get("/").status_code)

print("[2] customer registers + shops")
reg("testcust", "customer")
p = Product.objects.order_by("id").first()
r = c.post("/cart/add/", {"product_id": str(p.id), "quantity": "1"})
print("  add to cart:", r.status_code, "->", r.get("Location"))
print("  view cart:", c.get("/cart/").status_code)

before = Order.objects.count()
r = c.post("/orders/checkout/")
print("  checkout:", r.status_code, "->", r.get("Location"), "| orders:", Order.objects.count() - before, "new")

print("[3] customer submits a review (ML sentiment)")
r = c.post(f"/reviews/add/{p.id}/", {"rating": "5",
                                     "text": "I absolutely love this product, wonderful quality and fast delivery!"})
rev = Review.objects.filter(product=p, user__username="testcust").first()
print("  review status:", r.status_code, "| sentiment:", rev.sentiment_label, round(rev.sentiment_confidence, 3))

print("[4] authorization: customer blocked from staff dashboard")
r = c.get("/accounts/dashboard/")
print("  customer -> dashboard:", r.status_code, "(expect 302/403)")

print("[5] staff registers and opens demand dashboard (calls FastAPI /demand)")
c2 = Client(SERVER_NAME="127.0.0.1")
r = c2.post("/accounts/register/", {"username": "teststaff", "email": "s@demo.com",
                                    "password1": PW, "password2": PW, "role": "staff"})
print("  register staff:", r.status_code)
r = c2.get("/accounts/dashboard/")
body = r.content.decode().lower()
print("  staff -> dashboard:", r.status_code, "| shows forecast:", ("predicted" in body or "forecast" in body))
print("\nALL CHECKS DONE")

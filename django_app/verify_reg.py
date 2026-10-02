"""Verify registration now accepts an easy (weak) password."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings")
django.setup()

from django.test import Client
from django.contrib.auth.models import User

c = Client(SERVER_NAME="127.0.0.1")
# intentionally weak password 'a' to prove rules are relaxed
r = c.post("/accounts/register/", {
    "username": "easytest", "email": "",
    "password1": "a", "password2": "a", "role": "customer",
})
print("register weak-password status:", r.status_code, "->", r.get("Location"))
ok = User.objects.filter(username="easytest").exists()
print("user created:", ok)
if ok:
    User.objects.filter(username="easytest").delete()
    print("cleaned up test user")

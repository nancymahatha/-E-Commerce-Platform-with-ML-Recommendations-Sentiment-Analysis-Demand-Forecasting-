"""
Create demo accounts for testing auth + authorization.
(customer = shop/review only, staff = + demand dashboard, admin = superuser)

Run:  python seed_users.py
These are throwaway dev accounts; change the passwords before any real deploy.
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ecommerce.settings")
django.setup()

from django.contrib.auth.models import User
from accounts.models import UserProfile

DEMO = [
    ("customer1", "DemoPass1234", "customer1@demo.com", "customer"),
    ("staff1", "DemoPass1234", "staff1@demo.com", "staff"),
    ("admin1", "DemoPass1234", "admin1@demo.com", "admin"),
]

for username, password, email, role in DEMO:
    user, created = User.objects.get_or_create(username=username, defaults={"email": email})
    if created:
        user.set_password(password)
        if role == "admin":
            user.is_staff = True
            user.is_superuser = True
        user.save()
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.save()
    print(f"{'created' if created else 'exists'}  {username}  (role={role})")

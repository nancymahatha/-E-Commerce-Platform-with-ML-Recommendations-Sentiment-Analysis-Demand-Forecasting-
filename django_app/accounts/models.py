"""User profiles + roles for AUTHORIZATION.

We keep Django's built-in User for authentication (username/password hashing) and
add a UserProfile with a `role` for authorization:
  - customer : can shop, review, view their orders
  - staff     : the above + can open the demand-forecast dashboard
  - admin     : same as staff (used for the Django admin too)

A signal auto-creates a profile (default 'customer') whenever a User is created,
so we never have a User without a profile.
"""
from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


ROLE_CHOICES = [
    ("customer", "Customer"),
    ("staff", "Staff"),
    ("admin", "Admin"),
]


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="customer")
    phone = models.CharField(max_length=20, blank=True)

    def is_staff_role(self):
        return self.role in ("staff", "admin")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

"""Admin site branding + the CRUD entry point for non-technical staff.

The whole shop is manageable from /admin/:
  * Products & Categories  -> add / edit / delete
  * Orders                 -> view orders, change status
  * Reviews                -> read, moderate, delete (keeps the mood + confidence)
  * Users & Roles          -> create users, change who is staff/admin
"""
from django.contrib import admin

# Friendly titles so staff see "Lumina Store Admin", not "Django administration".
admin.site.site_header = "Lumina Store — Admin"
admin.site.site_title = "Lumina Store Admin"
admin.site.index_title = "Manage your store"

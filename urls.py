"""Django URL configuration."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    # Admin is at root because Django is mounted at /admin
    path('', admin.site.urls),
]

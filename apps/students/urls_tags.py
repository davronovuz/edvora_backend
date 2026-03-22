"""
Edvora - Tags URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TagViewSet

router = DefaultRouter()
router.register('', TagViewSet, basename='tags')

urlpatterns = [
    path('', include(router.urls)),
]

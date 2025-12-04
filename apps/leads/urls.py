"""
Edvora - Leads URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet, LeadActivityViewSet

router = DefaultRouter()
router.register('leads', LeadViewSet, basename='leads')
router.register('lead-activities', LeadActivityViewSet, basename='lead-activities')

urlpatterns = [
    path('', include(router.urls)),
]
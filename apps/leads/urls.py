"""
Edvora - Leads URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LeadViewSet, LeadActivityViewSet, DemoRequestViewSet

router = DefaultRouter()
router.register('leads', LeadViewSet, basename='leads')
router.register('lead-activities', LeadActivityViewSet, basename='lead-activities')
router.register('demo-requests', DemoRequestViewSet, basename='demo-requests')

urlpatterns = [
    path('', include(router.urls)),
]
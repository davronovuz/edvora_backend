"""
Edvora - Payments URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, InvoiceViewSet, DiscountViewSet

router = DefaultRouter()
router.register('payments', PaymentViewSet, basename='payments')
router.register('invoices', InvoiceViewSet, basename='invoices')
router.register('discounts', DiscountViewSet, basename='discounts')

urlpatterns = [
    path('', include(router.urls)),
]
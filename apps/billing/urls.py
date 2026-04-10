"""
Edvora - Billing URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    BillingProfileViewSet,
    StudentLeaveViewSet,
    DiscountViewSet,
    InvoiceViewSet,
)

router = DefaultRouter()
router.register('profiles', BillingProfileViewSet, basename='billing-profiles')
router.register('leaves', StudentLeaveViewSet, basename='billing-leaves')
router.register('discounts', DiscountViewSet, basename='billing-discounts')
router.register('invoices', InvoiceViewSet, basename='billing-invoices')

app_name = 'billing'

urlpatterns = [
    path('', include(router.urls)),
]

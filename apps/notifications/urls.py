"""
Edvora - Notifications URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet,
    NotificationTemplateViewSet,
    NotificationLogViewSet
)

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('notification-templates', NotificationTemplateViewSet, basename='notification-templates')
router.register('notification-logs', NotificationLogViewSet, basename='notification-logs')

urlpatterns = [
    path('', include(router.urls)),
]
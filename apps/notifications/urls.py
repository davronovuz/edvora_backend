"""
Edvora - Notifications URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NotificationViewSet,
    NotificationTemplateViewSet,
    NotificationLogViewSet,
    AutoSMSViewSet,
    ReminderViewSet,
)

router = DefaultRouter()
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('notification-templates', NotificationTemplateViewSet, basename='notification-templates')
router.register('notification-logs', NotificationLogViewSet, basename='notification-logs')
router.register('auto-sms', AutoSMSViewSet, basename='auto-sms')
router.register('reminders', ReminderViewSet, basename='reminders')

urlpatterns = [
    path('', include(router.urls)),
]
"""
Edvora - Students URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, StudentGroupNoteViewSet

router = DefaultRouter()
router.register('group-notes', StudentGroupNoteViewSet, basename='student-group-notes')
router.register('', StudentViewSet, basename='students')

urlpatterns = [
    path('', include(router.urls)),
]
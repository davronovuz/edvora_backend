"""
Edvora - Courses URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubjectViewSet, CourseViewSet

router = DefaultRouter()
router.register('subjects', SubjectViewSet, basename='subjects')
router.register('courses', CourseViewSet, basename='courses')

urlpatterns = [
    path('', include(router.urls)),
]
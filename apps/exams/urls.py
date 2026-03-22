"""
Edvora - Exams URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExamViewSet, ExamResultViewSet,
    HomeworkViewSet, HomeworkSubmissionViewSet,
    LessonPlanViewSet,
)

router = DefaultRouter()
router.register('exams', ExamViewSet)
router.register('exam-results', ExamResultViewSet)
router.register('homeworks', HomeworkViewSet)
router.register('homework-submissions', HomeworkSubmissionViewSet)
router.register('lesson-plans', LessonPlanViewSet)

urlpatterns = [
    path('', include(router.urls)),
]

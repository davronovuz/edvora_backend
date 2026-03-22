"""
Edvora - Exam Factory
"""

import factory
from django.utils import timezone
from apps.exams.models import Exam, ExamResult, Homework, HomeworkSubmission
from .group_factory import GroupFactory
from .student_factory import StudentFactory


class ExamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Exam

    group = factory.SubFactory(GroupFactory)
    title = factory.Sequence(lambda n: f"Exam {n + 1}")
    exam_type = 'quiz'
    max_score = 100
    passing_score = 60
    exam_date = factory.LazyFunction(lambda: timezone.now().date())
    duration_minutes = 60
    status = 'scheduled'


class ExamResultFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExamResult

    exam = factory.SubFactory(ExamFactory)
    student = factory.SubFactory(StudentFactory)
    score = 85
    status = 'graded'


class HomeworkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Homework

    group = factory.SubFactory(GroupFactory)
    title = factory.Sequence(lambda n: f"Homework {n + 1}")
    description = "Test homework description"
    max_score = 10
    assigned_date = factory.LazyFunction(lambda: timezone.now().date())
    due_date = factory.LazyFunction(lambda: (timezone.now() + timezone.timedelta(days=7)).date())
    status = 'active'

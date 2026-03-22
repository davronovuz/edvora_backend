"""
Course & Subject Factories
"""

import factory
from factory.django import DjangoModelFactory
from apps.courses.models import Subject, Course


class SubjectFactory(DjangoModelFactory):
    class Meta:
        model = Subject

    name = factory.Sequence(lambda n: f'Subject {n}')
    slug = factory.Sequence(lambda n: f'subject-{n}')
    is_active = True


class CourseFactory(DjangoModelFactory):
    class Meta:
        model = Course

    name = factory.Sequence(lambda n: f'Course {n}')
    subject = factory.SubFactory(SubjectFactory)
    level = 'beginner'
    duration_months = 3
    total_lessons = 36
    price = 500000
    is_active = True
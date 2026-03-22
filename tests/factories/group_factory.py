"""
Group Factory
"""

import factory
from factory.django import DjangoModelFactory
from django.utils import timezone
from apps.groups.models import Group, GroupStudent


class GroupFactory(DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Sequence(lambda n: f'Group-{n}')
    course = factory.SubFactory('tests.factories.course_factory.CourseFactory')
    teacher = factory.SubFactory('tests.factories.teacher_factory.TeacherFactory')
    start_date = factory.LazyFunction(timezone.now().date)
    days = [0, 2, 4]  # Mon, Wed, Fri
    start_time = '09:00'
    end_time = '11:00'
    max_students = 15
    status = 'active'


class GroupStudentFactory(DjangoModelFactory):
    class Meta:
        model = GroupStudent

    group = factory.SubFactory(GroupFactory)
    student = factory.SubFactory('tests.factories.student_factory.StudentFactory')
    is_active = True
    status = 'active'
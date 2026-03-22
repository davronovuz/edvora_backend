"""
Teacher Factory
"""

import factory
from factory.django import DjangoModelFactory
from apps.teachers.models import Teacher


class TeacherFactory(DjangoModelFactory):
    class Meta:
        model = Teacher

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone = factory.Sequence(lambda n: f'+99891000{n:04d}')
    email = factory.LazyAttribute(lambda o: f'{o.first_name.lower()}.teacher@test.com')
    status = 'active'
    salary_type = 'fixed'
    salary_amount = 3000000
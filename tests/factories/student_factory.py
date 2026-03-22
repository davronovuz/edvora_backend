"""
Student Factory
"""

import factory
from factory.django import DjangoModelFactory
from apps.students.models import Student


class StudentFactory(DjangoModelFactory):
    class Meta:
        model = Student

    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone = factory.Sequence(lambda n: f'+99890000{n:04d}')
    email = factory.LazyAttribute(lambda o: f'{o.first_name.lower()}@test.com')
    status = 'active'
    balance = 0
    source = 'walk_in'
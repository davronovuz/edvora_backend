"""
User Factory
"""

import factory
from factory.django import DjangoModelFactory
from apps.users.models import User


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f'user{n}@test.com')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    phone = factory.Sequence(lambda n: f'+99890123{n:04d}')
    role = 'admin'
    is_active = True

    @factory.lazy_attribute
    def password(self):
        return 'testpass123'

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        password = kwargs.pop('password', 'testpass123')
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user
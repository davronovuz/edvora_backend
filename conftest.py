"""
Edvora - Pytest Configuration
"""

import pytest
from django.conf import settings


def pytest_configure():
    settings.DATABASES['default']['NAME'] = 'edvora_test'


@pytest.fixture(scope='session')
def django_db_setup(django_test_environment, django_db_blocker):
    """Test database setup with tenant schema"""
    from django.test.utils import setup_databases, teardown_databases

    with django_db_blocker.unblock():
        db_cfg = setup_databases(
            verbosity=0,
            interactive=False,
            keepdb=False,
        )

        # Public tenant yaratish
        from apps.shared.models import Tenant, Domain
        from django.db import connection

        tenant, created = Tenant.objects.get_or_create(
            schema_name='test',
            defaults={
                'name': 'Test Markaz',
                'slug': 'test-markaz',
                'owner_name': 'Test Owner',
                'owner_email': 'owner@test.com',
                'owner_phone': '+998901234567',
                'status': 'active',
            }
        )

        if created:
            Domain.objects.get_or_create(
                domain='test.localhost',
                defaults={'tenant': tenant, 'is_primary': True}
            )

        # Tenant schema'ga o'tish
        connection.set_tenant(tenant)

    yield

    with django_db_blocker.unblock():
        # DB ni saqlaymiz (--reuse-db)
        pass


@pytest.fixture
def api_client():
    """API Client"""
    from rest_framework.test import APIClient
    client = APIClient()
    client.defaults['HTTP_HOST'] = 'test.localhost'
    return client


@pytest.fixture
def create_user(db):
    """User yaratish helper"""

    def make_user(**kwargs):
        from apps.users.models import User
        defaults = {
            'email': 'test@test.com',
            'password': 'testpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'owner',
        }
        defaults.update(kwargs)
        password = defaults.pop('password')
        user = User.objects.create(**defaults)
        user.set_password(password)
        user.save()
        return user

    return make_user


@pytest.fixture
def owner_user(create_user):
    """Owner user"""
    return create_user(
        email='owner@test.com',
        role='owner',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def admin_user(create_user):
    """Admin user"""
    return create_user(
        email='admin@test.com',
        role='admin'
    )


@pytest.fixture
def authenticated_client(api_client, owner_user):
    """Authenticated API Client"""
    api_client.force_authenticate(user=owner_user)
    return api_client


@pytest.fixture
def create_student(db):
    """Student yaratish helper"""

    def make_student(**kwargs):
        from apps.students.models import Student
        defaults = {
            'first_name': 'Test',
            'last_name': 'Student',
            'phone': '+998901234567',
            'status': 'active',
            'source': 'walk_in',
        }
        defaults.update(kwargs)
        return Student.objects.create(**defaults)

    return make_student


@pytest.fixture
def create_teacher(db):
    """Teacher yaratish helper"""

    def make_teacher(**kwargs):
        from apps.teachers.models import Teacher
        defaults = {
            'first_name': 'Test',
            'last_name': 'Teacher',
            'phone': '+998901234568',
            'status': 'active',
            'salary_type': 'fixed',
            'salary_amount': 3000000,
        }
        defaults.update(kwargs)
        return Teacher.objects.create(**defaults)

    return make_teacher


@pytest.fixture
def create_subject(db):
    """Subject yaratish helper"""

    def make_subject(**kwargs):
        from apps.courses.models import Subject
        defaults = {
            'name': 'Test Subject',
            'slug': 'test-subject',
            'is_active': True,
        }
        defaults.update(kwargs)
        obj, _ = Subject.objects.get_or_create(
            slug=defaults.pop('slug'),
            defaults=defaults,
        )
        return obj

    return make_subject


@pytest.fixture
def create_course(db, create_subject):
    """Course yaratish helper"""

    def make_course(**kwargs):
        from apps.courses.models import Course
        if 'subject' not in kwargs:
            kwargs['subject'] = create_subject()
        defaults = {
            'name': 'Test Course',
            'level': 'beginner',
            'duration_months': 3,
            'total_lessons': 36,
            'price': 500000,
            'is_active': True,
        }
        defaults.update(kwargs)
        return Course.objects.create(**defaults)

    return make_course


@pytest.fixture
def create_group(db, create_course, create_teacher):
    """Group yaratish helper"""

    def make_group(**kwargs):
        from apps.groups.models import Group
        from django.utils import timezone

        if 'course' not in kwargs:
            kwargs['course'] = create_course()
        if 'teacher' not in kwargs:
            kwargs['teacher'] = create_teacher()

        defaults = {
            'name': 'Test Group',
            'start_date': timezone.now().date(),
            'days': [0, 2, 4],
            'start_time': '09:00',
            'end_time': '11:00',
            'max_students': 15,
            'status': 'active',
        }
        defaults.update(kwargs)
        return Group.objects.create(**defaults)

    return make_group


@pytest.fixture
def create_room(db):
    """Room yaratish helper"""

    def make_room(**kwargs):
        from apps.rooms.models import Room
        defaults = {
            'name': 'Test Xona',
            'number': '101',
            'floor': 1,
            'room_type': 'classroom',
            'capacity': 20,
            'status': 'active',
        }
        defaults.update(kwargs)
        return Room.objects.create(**defaults)

    return make_room


@pytest.fixture
def create_exam(db, create_group):
    """Exam yaratish helper"""

    def make_exam(**kwargs):
        from apps.exams.models import Exam
        from django.utils import timezone
        if 'group' not in kwargs:
            kwargs['group'] = create_group()
        defaults = {
            'title': 'Test Exam',
            'exam_type': 'quiz',
            'max_score': 100,
            'passing_score': 60,
            'exam_date': timezone.now().date(),
            'duration_minutes': 60,
            'status': 'scheduled',
        }
        defaults.update(kwargs)
        return Exam.objects.create(**defaults)

    return make_exam


@pytest.fixture
def teacher_user(create_user):
    """Teacher role user"""
    return create_user(
        email='teacher@test.com',
        role='teacher'
    )


@pytest.fixture
def accountant_user(create_user):
    """Accountant role user"""
    return create_user(
        email='accountant@test.com',
        role='accountant'
    )


@pytest.fixture
def registrar_user(create_user):
    """Registrar role user"""
    return create_user(
        email='registrar@test.com',
        role='registrar'
    )

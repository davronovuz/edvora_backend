"""
Edvora - Branch (Filial) Tests
"""

import pytest
from apps.branches.models import Branch


# ==================== MODEL TESTS ====================

@pytest.mark.django_db
class TestBranchModel:
    def test_create_branch(self):
        branch = Branch.objects.create(
            name='Asosiy filial',
            address='Toshkent sh., Chilonzor t.',
            phone='+998901234567',
            is_main=True,
        )
        assert branch.name == 'Asosiy filial'
        assert branch.is_main is True
        assert str(branch) == 'Asosiy filial'

    def test_branch_default_status(self):
        branch = Branch.objects.create(name='Test', address='Test manzil')
        assert branch.status == 'active'
        assert branch.is_active is True

    def test_branch_inactive(self):
        branch = Branch.objects.create(
            name='Yopilgan', address='Test', status='inactive'
        )
        assert branch.is_active is False

    def test_branch_with_full_details(self):
        branch = Branch.objects.create(
            name='Najot filiali',
            address='Toshkent, Yunusobod',
            phone='+998901111111',
            city='Toshkent',
            district='Yunusobod',
            landmark='Metro yonida',
            latitude=41.311158,
            longitude=69.279737,
            working_hours={'start': '08:00', 'end': '21:00'},
            working_days=[0, 1, 2, 3, 4, 5],
            manager_name='Ali Valiyev',
            manager_phone='+998902222222',
        )
        assert branch.city == 'Toshkent'
        assert branch.latitude == pytest.approx(41.311158, abs=0.001)
        assert branch.working_hours['start'] == '08:00'

    def test_branch_ordering(self):
        """is_main=True birinchi, keyin alifbo bo'yicha"""
        Branch.objects.create(name='Chilonzor', address='a', is_main=False)
        Branch.objects.create(name='Asosiy', address='b', is_main=True)
        Branch.objects.create(name='Yunusobod', address='c', is_main=False)

        branches = list(Branch.objects.values_list('name', flat=True))
        assert branches[0] == 'Asosiy'

    def test_branch_counts_empty(self):
        branch = Branch.objects.create(name='Bo\'sh', address='Test')
        assert branch.groups_count == 0
        assert branch.rooms_count == 0
        assert branch.teachers_count == 0
        assert branch.students_count == 0


@pytest.mark.django_db
class TestBranchRelations:
    def test_student_with_branch(self, create_student):
        branch = Branch.objects.create(name='Filial 1', address='Test')
        student = create_student(branch=branch)
        assert student.branch == branch
        assert branch.students.count() == 1

    def test_group_with_branch(self, create_group):
        branch = Branch.objects.create(name='Filial 1', address='Test')
        group = create_group(branch=branch)
        assert group.branch == branch
        assert branch.groups.count() == 1

    def test_room_with_branch(self, create_room):
        branch = Branch.objects.create(name='Filial 1', address='Test')
        room = create_room(branch=branch)
        assert room.branch == branch
        assert branch.rooms.count() == 1

    def test_teacher_with_branch(self, create_teacher):
        branch = Branch.objects.create(name='Filial 1', address='Test')
        teacher = create_teacher(branch=branch)
        assert teacher.branch == branch
        assert branch.teachers.count() == 1

    def test_branch_counts(self, create_student, create_group, create_room, create_teacher):
        branch = Branch.objects.create(name='Filial', address='Test')
        create_student(branch=branch, phone='+998901111111')
        create_student(branch=branch, phone='+998902222222')
        create_group(branch=branch)
        create_room(branch=branch)
        create_teacher(branch=branch, phone='+998903333333')

        assert branch.students_count == 2
        assert branch.groups_count == 1
        assert branch.rooms_count == 1
        assert branch.teachers_count == 1

    def test_models_without_branch(self, create_student, create_group):
        """branch nullable - barcha modellar branchsiz ham ishlashi kerak"""
        student = create_student()
        assert student.branch is None

        group = create_group()
        assert group.branch is None


# ==================== API TESTS ====================

@pytest.mark.django_db
class TestBranchAPI:
    def test_create_branch(self, authenticated_client):
        resp = authenticated_client.post('/api/v1/branches/', {
            'name': 'Yangi filial',
            'address': 'Toshkent, Sergeli',
            'phone': '+998901234567',
            'city': 'Toshkent',
        })
        assert resp.status_code == 201
        assert resp.data['name'] == 'Yangi filial'

    def test_list_branches(self, authenticated_client):
        Branch.objects.create(name='Filial 1', address='a')
        Branch.objects.create(name='Filial 2', address='b')
        resp = authenticated_client.get('/api/v1/branches/')
        assert resp.status_code == 200

    def test_retrieve_branch(self, authenticated_client):
        branch = Branch.objects.create(
            name='Detail filial', address='Test manzil',
            city='Toshkent', manager_name='Ali',
        )
        resp = authenticated_client.get(f'/api/v1/branches/{branch.id}/')
        assert resp.status_code == 200
        assert resp.data['name'] == 'Detail filial'
        assert resp.data['city'] == 'Toshkent'
        assert resp.data['manager_name'] == 'Ali'

    def test_update_branch(self, authenticated_client):
        branch = Branch.objects.create(name='Eski nom', address='a')
        resp = authenticated_client.patch(f'/api/v1/branches/{branch.id}/', {
            'name': 'Yangi nom',
        })
        assert resp.status_code == 200
        assert resp.data['name'] == 'Yangi nom'

    def test_delete_branch(self, authenticated_client):
        branch = Branch.objects.create(name='O\'chirish', address='a')
        resp = authenticated_client.delete(f'/api/v1/branches/{branch.id}/')
        assert resp.status_code == 204
        assert Branch.objects.filter(id=branch.id).count() == 0

    def test_search_branches(self, authenticated_client):
        Branch.objects.create(name='Chilonzor filiali', address='a')
        Branch.objects.create(name='Yunusobod filiali', address='b')
        resp = authenticated_client.get('/api/v1/branches/?search=chilon')
        assert resp.status_code == 200

    def test_filter_by_status(self, authenticated_client):
        Branch.objects.create(name='Faol', address='a', status='active')
        Branch.objects.create(name='Yopiq', address='b', status='inactive')
        resp = authenticated_client.get('/api/v1/branches/?status=active')
        assert resp.status_code == 200

    def test_filter_by_city(self, authenticated_client):
        Branch.objects.create(name='Tosh', address='a', city='Toshkent')
        Branch.objects.create(name='Sam', address='b', city='Samarqand')
        resp = authenticated_client.get('/api/v1/branches/?city=Toshkent')
        assert resp.status_code == 200

    def test_unauthenticated_access(self, api_client):
        resp = api_client.get('/api/v1/branches/')
        assert resp.status_code == 401

    def test_statistics_endpoint(self, authenticated_client, create_student, create_group):
        branch = Branch.objects.create(name='Stat filial', address='Test')
        create_student(branch=branch, phone='+998901111111')
        create_student(branch=branch, phone='+998902222222', balance=-100000)
        create_group(branch=branch)

        resp = authenticated_client.get(f'/api/v1/branches/{branch.id}/statistics/')
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['data']['students']['total'] == 2
        assert resp.data['data']['students']['debtors'] == 1

    def test_branch_list_shows_counts(self, authenticated_client, create_student):
        branch = Branch.objects.create(name='Count filial', address='Test')
        create_student(branch=branch, phone='+998901111111')
        create_student(branch=branch, phone='+998902222222')

        resp = authenticated_client.get(f'/api/v1/branches/{branch.id}/')
        assert resp.status_code == 200
        assert resp.data['students_count'] == 2

    def test_filter_students_by_branch(self, authenticated_client, create_student):
        branch1 = Branch.objects.create(name='F1', address='a')
        branch2 = Branch.objects.create(name='F2', address='b')
        create_student(branch=branch1, phone='+998901111111')
        create_student(branch=branch2, phone='+998902222222')

        resp = authenticated_client.get(f'/api/v1/students/?branch={branch1.id}')
        assert resp.status_code == 200

    def test_filter_groups_by_branch(self, authenticated_client, create_group):
        branch = Branch.objects.create(name='F1', address='a')
        create_group(branch=branch)

        resp = authenticated_client.get(f'/api/v1/groups/?branch={branch.id}')
        assert resp.status_code == 200

"""
Edvora - Tags Tests
"""

import pytest
from django.contrib.contenttypes.models import ContentType
from apps.students.tags import Tag, TaggedItem
from apps.students.models import Student


# ==================== MODEL TESTS ====================

@pytest.mark.django_db
class TestTagModel:
    def test_create_tag(self):
        tag = Tag.objects.create(name='VIP', color='#FF0000')
        assert tag.name == 'VIP'
        assert tag.color == '#FF0000'
        assert str(tag) == 'VIP'

    def test_tag_default_color(self):
        tag = Tag.objects.create(name='Default Color')
        assert tag.color == '#3B82F6'

    def test_tag_unique_name(self):
        Tag.objects.create(name='Unique')
        with pytest.raises(Exception):
            Tag.objects.create(name='Unique')

    def test_tag_with_description(self):
        tag = Tag.objects.create(name='Premium', description='Premium talabalar')
        assert tag.description == 'Premium talabalar'


@pytest.mark.django_db
class TestTaggedItemModel:
    def test_tag_student(self, create_student):
        student = create_student()
        tag = Tag.objects.create(name='VIP', color='#FF0000')
        ct = ContentType.objects.get_for_model(Student)

        tagged = TaggedItem.objects.create(
            tag=tag,
            content_type=ct,
            object_id=student.id,
        )
        assert tagged.tag == tag
        assert tagged.object_id == student.id
        assert 'VIP' in str(tagged)

    def test_unique_tag_per_object(self, create_student):
        student = create_student()
        tag = Tag.objects.create(name='VIP')
        ct = ContentType.objects.get_for_model(Student)

        TaggedItem.objects.create(tag=tag, content_type=ct, object_id=student.id)
        with pytest.raises(Exception):
            TaggedItem.objects.create(tag=tag, content_type=ct, object_id=student.id)

    def test_multiple_tags_per_student(self, create_student):
        student = create_student()
        ct = ContentType.objects.get_for_model(Student)
        tag1 = Tag.objects.create(name='VIP')
        tag2 = Tag.objects.create(name='Premium')

        TaggedItem.objects.create(tag=tag1, content_type=ct, object_id=student.id)
        TaggedItem.objects.create(tag=tag2, content_type=ct, object_id=student.id)

        tags = TaggedItem.objects.filter(content_type=ct, object_id=student.id)
        assert tags.count() == 2

    def test_same_tag_different_students(self, create_student):
        s1 = create_student(phone='+998901111111')
        s2 = create_student(phone='+998902222222')
        tag = Tag.objects.create(name='VIP')
        ct = ContentType.objects.get_for_model(Student)

        TaggedItem.objects.create(tag=tag, content_type=ct, object_id=s1.id)
        TaggedItem.objects.create(tag=tag, content_type=ct, object_id=s2.id)

        assert tag.tagged_items.count() == 2

    def test_cascade_delete_tag(self, create_student):
        student = create_student()
        tag = Tag.objects.create(name='Temp')
        ct = ContentType.objects.get_for_model(Student)
        TaggedItem.objects.create(tag=tag, content_type=ct, object_id=student.id)

        tag.delete()
        assert TaggedItem.objects.filter(content_type=ct, object_id=student.id).count() == 0


# ==================== API TESTS ====================

@pytest.mark.django_db
class TestTagAPI:
    """Tag CRUD API (/api/v1/tags/)"""

    def test_create_tag(self, authenticated_client):
        resp = authenticated_client.post('/api/v1/tags/', {
            'name': 'VIP',
            'color': '#FF0000',
        })
        assert resp.status_code == 201
        assert resp.data['name'] == 'VIP'

    def test_list_tags(self, authenticated_client):
        Tag.objects.create(name='Tag1')
        Tag.objects.create(name='Tag2')
        resp = authenticated_client.get('/api/v1/tags/')
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data.get('data', resp.data))
        assert len(results) >= 2

    def test_update_tag(self, authenticated_client):
        tag = Tag.objects.create(name='Old Name')
        resp = authenticated_client.patch(f'/api/v1/tags/{tag.id}/', {
            'name': 'New Name',
        })
        assert resp.status_code == 200
        assert resp.data['name'] == 'New Name'

    def test_delete_tag(self, authenticated_client):
        tag = Tag.objects.create(name='To Delete')
        resp = authenticated_client.delete(f'/api/v1/tags/{tag.id}/')
        assert resp.status_code == 204
        assert Tag.objects.filter(id=tag.id).count() == 0

    def test_search_tags(self, authenticated_client):
        Tag.objects.create(name='Premium')
        Tag.objects.create(name='VIP')
        resp = authenticated_client.get('/api/v1/tags/?search=prem')
        assert resp.status_code == 200
        results = resp.data.get('results', resp.data.get('data', resp.data))
        assert len(results) == 1

    def test_unauthenticated_access(self, api_client):
        resp = api_client.get('/api/v1/tags/')
        assert resp.status_code == 401


@pytest.mark.django_db
class TestStudentTagsAPI:
    """Student tags endpoint (/api/v1/students/{id}/tags/)"""

    def test_get_student_tags_empty(self, authenticated_client, create_student):
        student = create_student()
        resp = authenticated_client.get(f'/api/v1/students/{student.id}/tags/')
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert resp.data['data'] == []

    def test_add_tag_to_student(self, authenticated_client, create_student):
        student = create_student()
        tag = Tag.objects.create(name='VIP', color='#FF0000')

        resp = authenticated_client.post(
            f'/api/v1/students/{student.id}/tags/',
            {'tag_id': str(tag.id)},
        )
        assert resp.status_code == 201
        assert resp.data['success'] is True

    def test_add_tag_then_list(self, authenticated_client, create_student):
        student = create_student()
        tag = Tag.objects.create(name='VIP', color='#FF0000')

        authenticated_client.post(
            f'/api/v1/students/{student.id}/tags/',
            {'tag_id': str(tag.id)},
        )
        resp = authenticated_client.get(f'/api/v1/students/{student.id}/tags/')
        assert len(resp.data['data']) == 1
        assert resp.data['data'][0]['name'] == 'VIP'
        assert resp.data['data'][0]['color'] == '#FF0000'

    def test_add_duplicate_tag(self, authenticated_client, create_student):
        student = create_student()
        tag = Tag.objects.create(name='VIP')

        authenticated_client.post(
            f'/api/v1/students/{student.id}/tags/',
            {'tag_id': str(tag.id)},
        )
        resp = authenticated_client.post(
            f'/api/v1/students/{student.id}/tags/',
            {'tag_id': str(tag.id)},
        )
        assert resp.status_code == 200
        assert 'allaqachon' in resp.data['message']

    def test_add_tag_without_tag_id(self, authenticated_client, create_student):
        student = create_student()
        resp = authenticated_client.post(
            f'/api/v1/students/{student.id}/tags/', {},
        )
        assert resp.status_code == 400

    def test_add_nonexistent_tag(self, authenticated_client, create_student):
        import uuid
        student = create_student()
        resp = authenticated_client.post(
            f'/api/v1/students/{student.id}/tags/',
            {'tag_id': str(uuid.uuid4())},
        )
        assert resp.status_code == 404

    def test_delete_tag_from_student(self, authenticated_client, create_student):
        student = create_student()
        tag = Tag.objects.create(name='VIP')
        ct = ContentType.objects.get_for_model(Student)
        TaggedItem.objects.create(tag=tag, content_type=ct, object_id=student.id)

        resp = authenticated_client.delete(
            f'/api/v1/students/{student.id}/tags/{tag.id}/',
        )
        assert resp.status_code == 200
        assert resp.data['success'] is True
        assert TaggedItem.objects.filter(
            tag=tag, content_type=ct, object_id=student.id
        ).count() == 0

    def test_delete_nonexistent_tag_from_student(self, authenticated_client, create_student):
        import uuid
        student = create_student()
        resp = authenticated_client.delete(
            f'/api/v1/students/{student.id}/tags/{uuid.uuid4()}/',
        )
        assert resp.status_code == 404

"""
Edvora - Room Tests
Xonalar CRUD, jadval, mavjudlik tekshiruvi
"""

import pytest
from django.utils import timezone
from rest_framework import status


pytestmark = pytest.mark.django_db


class TestRoomCRUD:
    """Xona CRUD testlari"""

    def test_create_room(self, authenticated_client):
        data = {
            'name': 'Asosiy sinf',
            'number': '201',
            'floor': 2,
            'room_type': 'classroom',
            'capacity': 25,
            'has_projector': True,
            'has_air_conditioning': True,
        }
        response = authenticated_client.post('/api/v1/rooms/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['number'] == '201'

    def test_list_rooms(self, authenticated_client, create_room):
        create_room(number='101')
        create_room(number='102', name='Ikkinchi xona')

        response = authenticated_client.get('/api/v1/rooms/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 2

    def test_retrieve_room(self, authenticated_client, create_room):
        room = create_room()
        response = authenticated_client.get(f'/api/v1/rooms/{room.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['number'] == '101'

    def test_update_room(self, authenticated_client, create_room):
        room = create_room()
        data = {'name': 'Yangilangan xona', 'number': '101', 'capacity': 30,
                'room_type': 'classroom'}
        response = authenticated_client.put(f'/api/v1/rooms/{room.id}/', data, format='json')
        assert response.status_code == status.HTTP_200_OK

    def test_delete_room(self, authenticated_client, create_room):
        room = create_room()
        response = authenticated_client.delete(f'/api/v1/rooms/{room.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_filter_by_room_type(self, authenticated_client, create_room):
        create_room(number='101', room_type='classroom')
        create_room(number='102', room_type='lab', name='Lab')

        response = authenticated_client.get('/api/v1/rooms/?room_type=lab')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_filter_by_floor(self, authenticated_client, create_room):
        create_room(number='101', floor=1)
        create_room(number='201', floor=2, name='2-qavat')

        response = authenticated_client.get('/api/v1/rooms/?floor=2')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1


class TestRoomAvailability:
    """Xona mavjudligi testlari"""

    def test_room_available_when_no_groups(self, authenticated_client, create_room):
        room = create_room()
        today = timezone.now().date().isoformat()
        response = authenticated_client.get(
            f'/api/v1/rooms/{room.id}/availability/?date={today}&start_time=09:00&end_time=11:00'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['is_available'] is True

    def test_available_rooms_list(self, authenticated_client, create_room):
        create_room(number='101')
        create_room(number='102', name='Ikkinchi')

        today = timezone.now().date().isoformat()
        response = authenticated_client.get(
            f'/api/v1/rooms/available/?date={today}&start_time=09:00&end_time=11:00'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']) == 2


class TestRoomSchedule:
    """Xona jadvali testlari"""

    def test_room_schedule_empty(self, authenticated_client, create_room):
        room = create_room()
        today = timezone.now().date().isoformat()
        response = authenticated_client.get(
            f'/api/v1/rooms/{room.id}/schedule/?date={today}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['data']['schedule']) == 0


class TestRoomModel:
    """Room model testlari"""

    def test_room_str(self, create_room):
        room = create_room()
        assert '101' in str(room)
        assert "o'rin" in str(room)

    def test_room_is_available_property(self, create_room):
        room = create_room(status='active')
        assert room.is_available is True

        room.status = 'maintenance'
        assert room.is_available is False

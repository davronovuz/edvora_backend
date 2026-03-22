"""
Edvora - Leads Tests
Lead CRUD, pipeline, conversion
"""

import pytest
from django.utils import timezone
from rest_framework import status
from apps.leads.models import Lead, LeadActivity


pytestmark = pytest.mark.django_db


class TestLeadCRUD:
    """Lead CRUD testlari"""

    def test_create_lead(self, authenticated_client):
        data = {
            'first_name': 'Jasur',
            'phone': '+998901234567',
            'source': 'instagram',
            'status': 'new',
            'priority': 'medium',
        }
        response = authenticated_client.post('/api/v1/leads/', data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['first_name'] == 'Jasur'

    def test_list_leads(self, authenticated_client):
        Lead.objects.create(
            first_name='Test', phone='+998901111111',
            source='walk_in', status='new',
        )
        response = authenticated_client.get('/api/v1/leads/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_filter_by_status(self, authenticated_client):
        Lead.objects.create(
            first_name='New', phone='+998901111111',
            source='walk_in', status='new',
        )
        Lead.objects.create(
            first_name='Contacted', phone='+998902222222',
            source='walk_in', status='contacted',
        )

        response = authenticated_client.get('/api/v1/leads/?status=new')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_filter_by_priority(self, authenticated_client):
        Lead.objects.create(
            first_name='High', phone='+998901111111',
            source='walk_in', status='new', priority='high',
        )

        response = authenticated_client.get('/api/v1/leads/?priority=high')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['meta']['total'] == 1

    def test_update_lead(self, authenticated_client):
        lead = Lead.objects.create(
            first_name='Test', phone='+998901111111',
            source='walk_in', status='new',
        )

        data = {'status': 'contacted'}
        response = authenticated_client.patch(
            f'/api/v1/leads/{lead.id}/', data, format='json'
        )
        assert response.status_code == status.HTTP_200_OK


class TestLeadActivity:
    """Lead activity testlari"""

    def test_create_activity(self, authenticated_client):
        lead = Lead.objects.create(
            first_name='Test', phone='+998901111111',
            source='walk_in', status='new',
        )

        data = {
            'lead': str(lead.id),
            'activity_type': 'call',
            'description': 'Qo\'ng\'iroq qilindi',
            'call_duration': 120,
        }
        response = authenticated_client.post(
            '/api/v1/lead-activities/', data, format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED


class TestLeadModel:
    """Lead model testlari"""

    def test_full_name(self):
        lead = Lead(first_name='Jasur', last_name='Karimov')
        assert lead.full_name == 'Jasur Karimov'

    def test_full_name_without_lastname(self):
        lead = Lead(first_name='Jasur')
        assert lead.full_name == 'Jasur'

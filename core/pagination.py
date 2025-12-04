"""
Edvora - Custom Pagination
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    """
    Custom pagination class

    Response format:
    {
        "success": true,
        "data": [...],
        "meta": {
            "page": 1,
            "per_page": 20,
            "total": 100,
            "total_pages": 5,
            "has_next": true,
            "has_previous": false
        }
    }
    """
    page_size = 20
    page_size_query_param = 'per_page'
    max_page_size = 100
    page_query_param = 'page'

    def get_paginated_response(self, data):
        return Response({
            'success': True,
            'data': data,
            'meta': {
                'page': self.page.number,
                'per_page': self.get_page_size(self.request),
                'total': self.page.paginator.count,
                'total_pages': self.page.paginator.num_pages,
                'has_next': self.page.has_next(),
                'has_previous': self.page.has_previous(),
            }
        })

    def get_paginated_response_schema(self, schema):
        return {
            'type': 'object',
            'properties': {
                'success': {'type': 'boolean'},
                'data': schema,
                'meta': {
                    'type': 'object',
                    'properties': {
                        'page': {'type': 'integer'},
                        'per_page': {'type': 'integer'},
                        'total': {'type': 'integer'},
                        'total_pages': {'type': 'integer'},
                        'has_next': {'type': 'boolean'},
                        'has_previous': {'type': 'boolean'},
                    }
                }
            }
        }
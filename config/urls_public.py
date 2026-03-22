

from django.contrib import admin
from django.urls import path
from django.http import JsonResponse
from apps.leads.views import DemoRequestViewSet


def home(request):
    return JsonResponse({
        'name': 'MarkazEdu API',
        'version': '1.0.0',
        'description': "O'quv markazlar uchun CRM",
    })


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('api/v1/demo-requests/', DemoRequestViewSet.as_view({
        'post': 'create',
        'get': 'list',
    }), name='demo-requests'),
]


from django.contrib import admin
from django.urls import path
from django.http import JsonResponse


def home(request):
    return JsonResponse({
        'name': 'Edvora API',
        'version': '1.0.0',
        'description': "O'quv markazlar uchun CRM",
    })


urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
]
"""
Shared app views - Tenant info endpoint
"""

from django.http import JsonResponse
from django.conf import settings
from django_tenants.utils import get_tenant_model


def tenant_info(request):
    """
    Public endpoint - tenant ma'lumotlarini qaytaradi
    GET /api/v1/tenant-info/
    Login sahifasida markaz nomi, logosi, fon rasmi ko'rsatish uchun
    """
    tenant = request.tenant
    TenantModel = get_tenant_model()

    # Public schema bo'lsa - MarkazEdu default info
    if tenant.schema_name == 'public':
        return JsonResponse({
            'name': 'MarkazEdu',
            'logo': None,
            'login_background': None,
            'primary_color': '#1e40af',
            'is_main': True,
        })

    # Tenant schema - markaz ma'lumotlari
    logo_url = None
    if tenant.logo:
        logo_url = request.build_absolute_uri(tenant.logo.url)

    bg_url = None
    if tenant.login_background:
        bg_url = request.build_absolute_uri(tenant.login_background.url)

    return JsonResponse({
        'name': tenant.name,
        'logo': logo_url,
        'login_background': bg_url,
        'primary_color': getattr(tenant, 'primary_color', '#1e40af'),
        'is_main': False,
    })

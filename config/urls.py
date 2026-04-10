"""
MarkazEdu - Main URLs (FINAL)
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.shared.views import tenant_info

urlpatterns = [
    path('panel-d97/', admin.site.urls),

    # Tenant info (public - login sahifasi uchun)
    path('api/v1/tenant-info/', tenant_info, name='tenant-info'),

    # API v1
    path('api/v1/', include('apps.users.urls')),
    path('api/v1/', include('apps.courses.urls')),
    path('api/v1/students/', include('apps.students.urls')),
    path('api/v1/tags/', include('apps.students.urls_tags')),
    path('api/v1/teachers/', include('apps.teachers.urls')),
    path('api/v1/groups/', include('apps.groups.urls')),
    path('api/v1/attendance/', include('apps.attendance.urls')),
    path('api/v1/holidays/', include('apps.attendance.urls_holidays')),
    path('api/v1/', include('apps.payments.urls')),
    path('api/v1/finance/', include('apps.finance.urls')),
    path('api/v1/billing/', include('apps.billing.urls')),
    path('api/v1/', include('apps.leads.urls')),
    path('api/v1/', include('apps.notifications.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/rooms/', include('apps.rooms.urls')),
    path('api/v1/', include('apps.exams.urls')),
    path('api/v1/audit/', include('apps.audit.urls')),
    path('api/v1/branches/', include('apps.branches.urls')),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    try:
        import debug_toolbar

        urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]
    except ImportError:
        pass
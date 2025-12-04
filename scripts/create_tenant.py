from apps.shared.models import Tenant, Domain, Plan
from datetime import timedelta
from django.utils import timezone

# 1. Plan yaratish
plan, created = Plan.objects.get_or_create(
    slug='pro',
    defaults={
        'name': 'Pro',
        'plan_type': 'pro',
        'description': 'Professional tarif',
        'price_monthly': 350000,
        'price_yearly': 3500000,
        'max_students': 200,
        'max_groups': 15,
        'max_teachers': 10,
        'max_admins': 5,
        'features': Plan.get_default_features('pro'),
        'is_active': True,
        'is_popular': True,
    }
)
print(f"{'✅ Plan yaratildi' if created else 'ℹ️ Plan mavjud'}: {plan.name}")

# 2. Tenant yaratish
tenant, created = Tenant.objects.get_or_create(
    slug='demo',
    defaults={
        'schema_name': 'tenant_demo',
        'name': 'Demo Markaz',
        'owner_name': 'Admin User',
        'owner_email': 'admin@demo.com',
        'owner_phone': '+998901234567',
        'address': 'Toshkent, Chilonzor',
        'city': 'Toshkent',
        'plan': plan,
        'status': 'active',
        'trial_ends_at': timezone.now() + timedelta(days=14),
    }
)
print(f"{'✅ Tenant yaratildi' if created else 'ℹ️ Tenant mavjud'}: {tenant.name}")

# 3. Domain yaratish
domain, created = Domain.objects.get_or_create(
    domain='localhost',
    defaults={
        'tenant': tenant,
        'is_primary': True,
    }
)
print(f"{'✅ Domain yaratildi' if created else 'ℹ️ Domain mavjud'}: {domain.domain}")

print("\n" + "="*50)
print("🎉 Tenant tayyor!")
print(f"   Schema: {tenant.schema_name}")
print("="*50)

from django.db import connection
from apps.users.models import User

# Tenant schema'ga o'tish
connection.set_schema('tenant_demo')

# Superuser yaratish
user, created = User.objects.get_or_create(
    email='admin@demo.com',
    defaults={
        'first_name': 'Admin',
        'last_name': 'User',
        'phone': '+998901234567',
        'role': 'owner',
        'is_staff': True,
        'is_superuser': True,
        'is_active': True,
    }
)

if created:
    user.set_password('admin123')
    user.save()
    print("✅ Superuser yaratildi!")
else:
    print("ℹ️ Superuser mavjud")

print(f"   Email: admin@demo.com")
print(f"   Password: admin123")
print(f"   Role: {user.role}")

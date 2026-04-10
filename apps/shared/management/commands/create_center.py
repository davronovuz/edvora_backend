"""
O'quv markaz yaratish buyrug'i
Tenant + Domain + Owner user avtomatik yaratiladi

Foydalanish:
  python manage.py create_center --name "Ziyo Academy" --slug ziyo --domain ziyo.markazedu.uz --owner-email admin@ziyo.uz --owner-password ziyo2025 --owner-name "Alisher Karimov" --owner-phone "+998901234567"
"""

from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from apps.shared.models import Tenant, Domain


class Command(BaseCommand):
    help = "Yangi o'quv markaz (tenant) yaratish"

    def add_arguments(self, parser):
        parser.add_argument('--name', required=True, help="Markaz nomi")
        parser.add_argument('--slug', required=True, help="Slug (schema nomi)")
        parser.add_argument('--domain', required=True, help="Domain (masalan: ziyo.markazedu.uz)")
        parser.add_argument('--owner-name', required=True, help="Egasi ismi")
        parser.add_argument('--owner-email', required=True, help="Egasi email")
        parser.add_argument('--owner-password', required=True, help="Egasi paroli")
        parser.add_argument('--owner-phone', default='', help="Egasi telefoni")

    def handle(self, *args, **options):
        name = options['name']
        slug = options['slug']
        domain_name = options['domain']
        owner_name = options['owner_name']
        owner_email = options['owner_email']
        owner_password = options['owner_password']
        owner_phone = options['owner_phone']

        # 1. Tenant yaratish
        self.stdout.write(f"1. Tenant yaratilmoqda: {name} (schema: {slug})...")

        if Tenant.objects.filter(schema_name=slug).exists():
            self.stdout.write(self.style.ERROR(f"'{slug}' schema allaqachon mavjud!"))
            return

        tenant = Tenant.objects.create(
            schema_name=slug,
            name=name,
            slug=slug,
            owner_name=owner_name,
            owner_email=owner_email,
            owner_phone=owner_phone,
            status='active',
        )
        self.stdout.write(self.style.SUCCESS(f"   Tenant yaratildi: {tenant.name}"))

        # 2. Domain yaratish
        self.stdout.write(f"2. Domain yaratilmoqda: {domain_name}...")

        if Domain.objects.filter(domain=domain_name).exists():
            self.stdout.write(self.style.WARNING(f"   Domain allaqachon mavjud, o'tkazib yuborildi"))
        else:
            Domain.objects.create(
                domain=domain_name,
                tenant=tenant,
                is_primary=True,
            )
            self.stdout.write(self.style.SUCCESS(f"   Domain yaratildi: {domain_name}"))

        # 3. Owner user yaratish (tenant schema ichida)
        self.stdout.write(f"3. Owner user yaratilmoqda: {owner_email}...")

        with schema_context(slug):
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if User.objects.filter(email=owner_email).exists():
                self.stdout.write(self.style.WARNING(f"   User allaqachon mavjud, o'tkazib yuborildi"))
            else:
                user = User.objects.create_user(
                    email=owner_email,
                    password=owner_password,
                    full_name=owner_name,
                    phone=owner_phone,
                    role='owner',
                    is_staff=True,
                    is_superuser=True,
                )
                self.stdout.write(self.style.SUCCESS(f"   Owner yaratildi: {user.email}"))

        # Xulosa
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write(self.style.SUCCESS(f"O'quv markaz tayyor!"))
        self.stdout.write(f"  Markaz: {name}")
        self.stdout.write(f"  Domain: https://{domain_name}")
        self.stdout.write(f"  Login:  {owner_email} / {owner_password}")
        self.stdout.write(self.style.SUCCESS("=" * 50))
        self.stdout.write("")
        self.stdout.write("Qo'shimcha qadamlar:")
        self.stdout.write(f"  1. DNS: {slug} -> 144.91.118.72 (A record)")
        self.stdout.write(f"  2. SSL: certbot certonly --webroot -w /var/www/certbot -d {domain_name}")

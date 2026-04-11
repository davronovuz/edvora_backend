"""
Edvora - Users Serializers
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer
    Telefon raqam yoki email bilan login qilish
    """
    username_field = 'phone'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Default 'email' fieldni olib tashlab, 'phone' qo'shamiz
        self.fields.pop('email', None)
        self.fields['phone'] = serializers.CharField(required=True)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Custom claims
        token['email'] = user.email
        token['phone'] = user.phone
        token['role'] = user.role
        token['full_name'] = user.full_name

        return token

    def validate(self, attrs):
        phone = attrs.get('phone', '').strip()
        password = attrs.get('password', '')

        # Telefon raqam bo'yicha userni topish
        try:
            user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            # Email bilan ham tekshiramiz (backward compatibility)
            try:
                user = User.objects.get(email=phone)
            except User.DoesNotExist:
                raise serializers.ValidationError(
                    {'detail': "Telefon raqam yoki parol noto'g'ri"}
                )

        if not user.check_password(password):
            raise serializers.ValidationError(
                {'detail': "Telefon raqam yoki parol noto'g'ri"}
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {'detail': "Foydalanuvchi faol emas"}
            )

        # Token yaratish
        refresh = self.get_token(user)
        self.user = user

        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }

        # Response'ga qo'shimcha ma'lumotlar
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
            'phone': self.user.phone,
            'full_name': self.user.full_name,
            'role': self.user.role,
            'permissions': self.user.get_permissions_dict(),
        }

        return data


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer (list, retrieve)
    """
    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name',
            'full_name', 'avatar', 'role', 'role_display',
            'is_active', 'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    User yaratish serializer
    """
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'email', 'phone', 'first_name', 'last_name',
            'role', 'password', 'password_confirm'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': "Parollar mos kelmadi"
            })
        # Email bo'sh bo'lsa — telefon asosida auto-generate
        if not attrs.get('email'):
            phone = attrs.get('phone', '').replace('+', '').replace(' ', '')
            attrs['email'] = f"{phone}@user.local"
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    User tahrirlash serializer
    """

    class Meta:
        model = User
        fields = [
            'email', 'phone', 'first_name', 'last_name',
            'avatar', 'role', 'custom_permissions', 'is_active'
        ]


class ChangePasswordSerializer(serializers.Serializer):
    """
    Parol o'zgartirish
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': "Yangi parollar mos kelmadi"
            })
        return attrs


class UserPermissionsSerializer(serializers.ModelSerializer):
    """
    User permissions serializer
    """
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'role', 'custom_permissions', 'permissions']

    def get_permissions(self, obj):
        return obj.get_permissions_dict()


class MeSerializer(serializers.ModelSerializer):
    """
    Current user serializer (/auth/me)
    """
    full_name = serializers.ReadOnlyField()
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone', 'first_name', 'last_name',
            'full_name', 'avatar', 'role', 'role_display',
            'permissions', 'is_active', 'created_at', 'last_login'
        ]

    def get_permissions(self, obj):
        return obj.get_permissions_dict()
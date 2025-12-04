"""
Edvora - Users Serializers
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer
    Token ichiga qo'shimcha ma'lumotlar qo'shish
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['full_name'] = user.full_name

        return token

    def validate(self, attrs):
        data = super().validate(attrs)

        # Response'ga qo'shimcha ma'lumotlar
        data['user'] = {
            'id': str(self.user.id),
            'email': self.user.email,
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
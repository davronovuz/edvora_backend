"""
Edvora - Users Views
"""

from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from core.permissions import IsOwnerOrAdmin, RoleBasedPermission
from .models import User
from .serializers import (
    CustomTokenObtainPairSerializer,
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    UserPermissionsSerializer,
    MeSerializer,
)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Login endpoint
    """
    serializer_class = CustomTokenObtainPairSerializer


class MeView(generics.RetrieveUpdateAPIView):
    """
    Current user profile
    GET /api/v1/auth/me - Current user ma'lumotlari
    PUT /api/v1/auth/me - Profilni yangilash
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """
    Parol o'zgartirish
    POST /api/v1/auth/change-password
    """
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user

        # Check old password
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'INVALID_PASSWORD',
                        'message': "Joriy parol noto'g'ri"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Set new password
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response({
            'success': True,
            'message': "Parol muvaffaqiyatli o'zgartirildi"
        })


class UserViewSet(viewsets.ModelViewSet):
    """
    Users CRUD

    GET    /api/v1/users/          - List users
    POST   /api/v1/users/          - Create user
    GET    /api/v1/users/{id}/     - Get user
    PUT    /api/v1/users/{id}/     - Update user
    DELETE /api/v1/users/{id}/     - Delete user
    """
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated, RoleBasedPermission]

    role_permissions = {
        'list': ['owner', 'admin'],
        'retrieve': ['owner', 'admin'],
        'create': ['owner'],
        'update': ['owner'],
        'partial_update': ['owner'],
        'destroy': ['owner'],
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'permissions':
            return UserPermissionsSerializer
        return UserSerializer

    def get_queryset(self):
        """Owner/Admin faqat o'z tenant'idagi userlarni ko'radi"""
        return User.objects.all().order_by('-created_at')

    @action(detail=True, methods=['get', 'put'])
    def permissions(self, request, pk=None):
        """
        GET  /api/v1/users/{id}/permissions/ - User permissions
        PUT  /api/v1/users/{id}/permissions/ - Update permissions
        """
        user = self.get_object()

        if request.method == 'GET':
            serializer = UserPermissionsSerializer(user)
            return Response({
                'success': True,
                'data': serializer.data
            })

        elif request.method == 'PUT':
            # Only owner can change permissions
            if not request.user.is_owner():
                return Response(
                    {
                        'success': False,
                        'error': {
                            'code': 'PERMISSION_DENIED',
                            'message': "Faqat markaz egasi ruxsatlarni o'zgartira oladi"
                        }
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            user.custom_permissions = request.data.get('custom_permissions', {})
            user.save()

            serializer = UserPermissionsSerializer(user)
            return Response({
                'success': True,
                'data': serializer.data,
                'message': "Ruxsatlar yangilandi"
            })

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            # Xatolarni odam tushunadigan formatda qaytarish
            errors = serializer.errors
            first_error = None
            for field, msgs in errors.items():
                msg = msgs[0] if isinstance(msgs, list) else str(msgs)
                first_error = f"{field}: {msg}"
                break
            return Response({
                'success': False,
                'error': {'message': first_error or "Xatolik yuz berdi"},
                'details': errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        return Response({
            'success': True,
            'data': UserSerializer(user).data,
            'message': "Foydalanuvchi yaratildi"
        }, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()

        # Cannot delete yourself
        if user == request.user:
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'CANNOT_DELETE_SELF',
                        'message': "O'zingizni o'chira olmaysiz"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Cannot delete owner
        if user.is_owner():
            return Response(
                {
                    'success': False,
                    'error': {
                        'code': 'CANNOT_DELETE_OWNER',
                        'message': "Markaz egasini o'chirib bo'lmaydi"
                    }
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.delete()
        return Response({
            'success': True,
            'message': "Foydalanuvchi o'chirildi"
        }, status=status.HTTP_200_OK)
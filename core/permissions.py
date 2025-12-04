"""
Edvora - Custom Permissions
Role-based access control
"""

from rest_framework import permissions


class IsOwner(permissions.BasePermission):
    """
    Faqat Owner (markaz egasi) uchun
    """

    def has_permission(self, request, view):
        return (
                request.user and
                request.user.is_authenticated and
                request.user.role == 'owner'
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Owner yoki Admin uchun
    """

    def has_permission(self, request, view):
        return (
                request.user and
                request.user.is_authenticated and
                request.user.role in ['owner', 'admin']
        )


class IsTeacher(permissions.BasePermission):
    """
    O'qituvchi uchun
    """

    def has_permission(self, request, view):
        return (
                request.user and
                request.user.is_authenticated and
                request.user.role == 'teacher'
        )


class IsAccountant(permissions.BasePermission):
    """
    Buxgalter uchun
    """

    def has_permission(self, request, view):
        return (
                request.user and
                request.user.is_authenticated and
                request.user.role == 'accountant'
        )


class IsRegistrar(permissions.BasePermission):
    """
    Qabul bo'limi uchun
    """

    def has_permission(self, request, view):
        return (
                request.user and
                request.user.is_authenticated and
                request.user.role == 'registrar'
        )


class HasPermission(permissions.BasePermission):
    """
    Custom permission checker
    View'da permission_required attribute bo'lishi kerak

    Usage:
        class MyView(APIView):
            permission_classes = [HasPermission]
            permission_required = 'students.create'
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Owner has all permissions
        if request.user.role == 'owner':
            return True

        # Check specific permission
        required_permission = getattr(view, 'permission_required', None)
        if required_permission is None:
            return True

        return request.user.has_perm(required_permission)


class RoleBasedPermission(permissions.BasePermission):
    """
    Role-based permission with action mapping

    Usage:
        class MyViewSet(ModelViewSet):
            permission_classes = [RoleBasedPermission]
            role_permissions = {
                'list': ['owner', 'admin', 'teacher'],
                'create': ['owner', 'admin'],
                'update': ['owner', 'admin'],
                'destroy': ['owner'],
            }
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Owner has all permissions
        if request.user.role == 'owner':
            return True

        # Get action-based roles
        role_permissions = getattr(view, 'role_permissions', {})
        action = getattr(view, 'action', None)

        if action is None:
            # For non-viewset views, use request method
            method_action_map = {
                'GET': 'list',
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'partial_update',
                'DELETE': 'destroy',
            }
            action = method_action_map.get(request.method, 'list')

        allowed_roles = role_permissions.get(action, [])

        # If no roles specified, allow all authenticated users
        if not allowed_roles:
            return True

        return request.user.role in allowed_roles
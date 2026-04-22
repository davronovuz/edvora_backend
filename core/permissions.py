"""
Edvora - Custom Permissions
Role-based access control with custom permission support
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


# Action → permission mapping
# Basename (router.register) → action → permission key
_FINANCE_VIEW_ALL = {
    'list': 'finance.view', 'retrieve': 'finance.view',
    'create': 'finance.view', 'update': 'finance.view',
    'partial_update': 'finance.view', 'destroy': 'finance.view',
}

ACTION_PERMISSION_MAP = {
    'students': {
        'list': 'students.view', 'retrieve': 'students.view',
        'create': 'students.create', 'update': 'students.update',
        'partial_update': 'students.update', 'destroy': 'students.delete',
    },
    'teachers': {
        'list': 'teachers.view', 'retrieve': 'teachers.view',
        'create': 'teachers.create', 'update': 'teachers.update',
        'partial_update': 'teachers.update', 'destroy': 'teachers.delete',
    },
    'courses': {
        'list': 'courses.view', 'retrieve': 'courses.view',
        'create': 'courses.create', 'update': 'courses.update',
        'partial_update': 'courses.update', 'destroy': 'courses.delete',
    },
    'groups': {
        'list': 'groups.view', 'retrieve': 'groups.view',
        'create': 'groups.create', 'update': 'groups.update',
        'partial_update': 'groups.update', 'destroy': 'groups.delete',
        'students': 'groups.view', 'add_student': 'groups.update',
        'remove_student': 'groups.update', 'transfer_student': 'groups.update',
        'schedule_conflicts': 'groups.view',
        'summary': 'groups.view',
    },
    'attendance': {
        'list': 'attendance.view', 'retrieve': 'attendance.view',
        'create': 'attendance.mark', 'update': 'attendance.mark',
        'partial_update': 'attendance.mark', 'destroy': 'attendance.mark',
        'bulk_create': 'attendance.mark', 'by_group': 'attendance.view',
        'by_student': 'attendance.view', 'report': 'attendance.view',
    },
    'payments': {
        'list': 'payments.view', 'retrieve': 'payments.view',
        'create': 'payments.create', 'update': 'payments.create',
        'partial_update': 'payments.create', 'destroy': 'payments.refund',
    },
    'leads': {
        'list': 'leads.view', 'retrieve': 'leads.view',
        'create': 'leads.create', 'update': 'leads.update',
        'partial_update': 'leads.update', 'destroy': 'leads.update',
        'convert': 'leads.convert',
    },
    # Finance app — barcha view'lar finance.view permission
    'expenses': _FINANCE_VIEW_ALL,
    'expense-categories': _FINANCE_VIEW_ALL,
    'transactions': _FINANCE_VIEW_ALL,
    'finance-dashboard': _FINANCE_VIEW_ALL,
    'salaries': {
        'list': 'salaries.view', 'retrieve': 'salaries.view',
        'create': 'salaries.calculate', 'update': 'salaries.calculate',
        'partial_update': 'salaries.calculate', 'destroy': 'salaries.calculate',
        'calculate': 'salaries.calculate', 'approve': 'salaries.approve',
        'pay': 'salaries.pay',
    },
    # Billing app
    'billing-profiles': _FINANCE_VIEW_ALL,
    'billing-invoices': _FINANCE_VIEW_ALL,
    'billing-leaves': _FINANCE_VIEW_ALL,
    'billing-discounts': _FINANCE_VIEW_ALL,
    # Invoices (payments app)
    'invoices': _FINANCE_VIEW_ALL,
    'discounts': _FINANCE_VIEW_ALL,
}


class RoleBasedPermission(permissions.BasePermission):
    """
    Role-based permission with custom_permissions support.

    1. Owner — hamma narsaga ruxsat
    2. custom_permissions da ruxsat bor — ruxsat beradi
    3. role_permissions da role bor — ruxsat beradi
    4. Aks holda — rad

    Usage:
        class MyViewSet(ModelViewSet):
            permission_classes = [RoleBasedPermission]
            role_permissions = {
                'list': ['owner', 'admin', 'teacher'],
                'create': ['owner', 'admin'],
            }
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # Owner has all permissions
        if request.user.role == 'owner':
            return True

        # Action aniqlash
        action = getattr(view, 'action', None)
        if action is None:
            method_action_map = {
                'GET': 'list',
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'partial_update',
                'DELETE': 'destroy',
            }
            action = method_action_map.get(request.method, 'list')

        # Custom permission tekshirish (Settings'da berilgan ruxsatlar)
        custom_perm = self._check_custom_permission(request.user, view, action)
        if custom_perm is True:
            return True

        # Role-based tekshirish (legacy)
        role_permissions = getattr(view, 'role_permissions', {})
        allowed_roles = role_permissions.get(action, [])

        # Agar role_permissions da action yo'q — ruxsat berish
        if not allowed_roles:
            return True

        return request.user.role in allowed_roles

    def _check_custom_permission(self, user, view, action):
        """
        User ning custom_permissions dan tegishli permission bormi tekshirish.
        View nomi yoki view_permission_map orqali mapping qilinadi.
        """
        # View'da aniq permission ko'rsatilgan bo'lsa
        view_permission_map = getattr(view, 'view_permission_map', None)
        if view_permission_map:
            perm_key = view_permission_map.get(action)
            if perm_key and user.has_permission(perm_key):
                return True

        # Avtomatik mapping — ViewSet basename orqali
        basename = getattr(view, 'basename', None)
        if not basename:
            # ViewSet nomidan olish: StudentViewSet -> students, PaymentViewSet -> payments
            cls_name = view.__class__.__name__.lower()
            for suffix in ('viewset', 'view'):
                if cls_name.endswith(suffix):
                    cls_name = cls_name[:-len(suffix)]
                    break
            # Plural qilish (oddiy)
            basename = cls_name + 's' if not cls_name.endswith('s') else cls_name

        # ACTION_PERMISSION_MAP dan tekshirish
        resource_map = ACTION_PERMISSION_MAP.get(basename, {})
        perm_key = resource_map.get(action)
        if perm_key and user.has_permission(perm_key):
            return True

        return False

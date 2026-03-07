\"\"\"
Custom permissions for role-based access control.
\"\"\"

from rest_framework.permissions import BasePermission

class IsTeacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['TEACHER', 'CONTACT_PERSON', 'HEADTEACHER', 'BURSAR']

class IsContactPerson(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['CONTACT_PERSON', 'HEADTEACHER', 'BURSAR']

class IsHeadteacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['HEADTEACHER', 'BURSAR']

class IsBursar(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'BURSAR'

class IsBursarOrHeadteacher(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['BURSAR', 'HEADTEACHER']

class IsBoard(BasePermission):
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == 'BOARD':
            return request.method in ['GET', 'HEAD', 'OPTIONS']
        return request.user.role in ['BURSAR', 'HEADTEACHER']

class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['BURSAR', 'HEADTEACHER']:
            return True
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'recorded_by'):
            return obj.recorded_by == request.user
        if hasattr(obj, 'staff'):
            return obj.staff == request.user
        return False

class CanAccessClass(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role in ['BURSAR', 'HEADTEACHER']:
            return True
        school_class = getattr(obj, 'school_class', getattr(obj, 'assigned_class', None))
        return school_class and getattr(request.user, 'assigned_class', None) == school_class

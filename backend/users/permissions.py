from rest_framework import permissions


class IsSupervisionOrAdmin(permissions.BasePermission):

    def has_permission(self, request, view):
        return request.user.is_admin


class IsSupervisionOrAdminOrReadOnly(permissions.BasePermission):

    def has_permission(self, request, view):
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated
                and request.user.is_admin
                )


class IsAuthorOrModeratorChange(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        return (request.method in permissions.SAFE_METHODS
                or request.user.is_authenticated
                and (obj.author == request.user
                     or request.user.is_moderator
                     or request.user.is_admin)
                )

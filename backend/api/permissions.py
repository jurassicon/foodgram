from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Разрешает небезопасные методы (POST, PUT, PATCH, DELETE)
    только автору объекта. Остальным — возвращается 403.
    GET/HEAD/OPTIONS доступны всем.
    """

    def has_object_permission(self, request, view, obj):
        return (request.method in permissions.SAFE_METHODS or obj.author
                == request.user)

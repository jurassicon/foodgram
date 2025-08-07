from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from recipes.pagination import RecipesPagination
from users.models import Follow, User
from users.serializers import (
    AvatarSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
)


class UsersViewSet(UserViewSet):
    """
    This class provides API endpoints to manage user-related operations,
    including retrieving user details, user creation, managing user
    subscriptions, and handling user avatars. It allows customization of
    serializer and permissions based on the specific action being performed.

    The class extends from UserViewSet and provides additional functionality
    while reusing the base implementation for common user management.
    """
    lookup_field = 'pk'
    serializer_class = UserSerializer
    queryset = User.objects.all()
    pagination_class = RecipesPagination

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'create'):
            return [AllowAny()]
        return [IsAuthenticated()]

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated, ],
        parser_classes=[MultiPartParser, JSONParser],
    )
    def avatar(self, request):
        user = request.user
        if request.method == 'GET':
            return Response(
                {'avatar': user.avatar.url if user.avatar else None},
                status=status.HTTP_200_OK
            )

        elif request.method == 'PUT':
            serializer = AvatarSerializer(
                user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        url_path='me',
        url_name='me',
        methods=['GET'],
        permission_classes=[IsAuthenticated],
    )
    def me_url(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                user, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(user, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        url_path='subscribe',
        permission_classes=[IsAuthenticated],
        serializer_class=UserWithRecipesSerializer,
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        user = request.user
        if request.method == 'POST' and author == user:
            return Response(
                {'detail': 'Нельзя подписаться на самого себя'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if request.method == 'POST':
            follow, created = Follow.objects.get_or_create(
                user=user,
                following=author
            )
            if not created:
                return Response(
                    {'detail': 'Вы уже подписаны'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            data = self.get_serializer(
                author, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Follow.objects.filter(
            user=user, following=author
        ).delete()
        if not deleted:
            return Response({'detail': 'Вы не были подписаны'},
                            status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False, methods=['GET'],
        url_path='subscriptions',
        permission_classes=[IsAuthenticated],
        serializer_class=UserWithRecipesSerializer,
    )
    def subscriptions(self, request):
        user = request.user
        qs = User.objects.filter(following__user=user)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = UserWithRecipesSerializer(
            qs, many=True, context={'request': request}
        )
        return Response(serializer.data)

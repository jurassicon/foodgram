from django.shortcuts import get_object_or_404
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from recipes.pagination import CustomUserPagination
from .models import User, Follow
from .serializers import UserRegistrationSerializer, UserSerializer, \
    AvatarSerializer, UserWithRecipesSerializer


class CustomUserViewSet(UserViewSet):
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
    pagination_class = CustomUserPagination

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'create'):
            return [AllowAny()]
        return [IsAuthenticated()]

    def get_queryset(self):
        return User.objects.all()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        if self.action == 'set_password':
            return SetPasswordSerializer
        if self.action in ('subscriptions', 'subscribe'):
            return UserWithRecipesSerializer
        return UserSerializer

    @action(
        detail=False,
        methods=['put', 'get', 'delete'],
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

        elif request.method == 'DELETE':
            user.avatar = None
            user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(
        detail=False,
        url_path='me',
        url_name='me',
        methods=['GET', 'PATCH'],
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
    )
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        user = request.user
        if request.method == 'POST':
            if (author == user or Follow.objects.filter(
                    user=user,
                    following=author
            ).exists()):

                return Response({'detail': 'Ошибка подписки'},
                                status.HTTP_400_BAD_REQUEST)
            Follow.objects.create(user=user, following=author)
            serializer = self.get_serializer(author,
                                             context={'request': request})
            return Response(serializer.data, status.HTTP_201_CREATED)

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
    )
    def subscriptions(self, request):
        user = request.user
        follows = Follow.objects.filter(user=user).values_list(
            'following', flat=True
        )
        qs = User.objects.filter(pk__in=follows)
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

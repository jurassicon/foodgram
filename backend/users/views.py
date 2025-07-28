from django.shortcuts import get_object_or_404
from djoser.serializers import SetPasswordSerializer
from djoser.views import UserViewSet
from rest_framework import (
    permissions)
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
    lookup_field = 'pk'
    serializer_class = UserSerializer
    queryset = User.objects.all()
    pagination_class = CustomUserPagination

    def get_permissions(self):
        # 1) Для list и retrieve — разрешаем всем
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # повторно сериализуем тем же сериализатором, чтобы вернуть id, email, username…
        out = UserRegistrationSerializer(user)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=['put', 'get', 'delete'],
        url_path='me/avatar',
        permission_classes=[IsAuthenticated, ],
        parser_classes=[MultiPartParser, JSONParser],
    )
    def avatar(self, request):
        """
        GET  /api/users/me/avatar/ — вернуть URL текущего аватара
        PUT  /api/users/me/avatar/ — загрузить новый аватар
        """
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
        methods=['GET', 'PATCH'],
        permission_classes=[permissions.IsAuthenticated, ],
    )
    def me_url(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(
                user, data=request.data,partial=True
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
        """
        POST /api/users/{pk}/subscribe/ — подписаться / отписаться
        Возвращает UserWithRecipesSerializer для {pk}.
        """
        author = get_object_or_404(User, pk=pk)
        user = request.user
        if request.method == 'POST':
            if author == user or Follow.objects.filter(user=user,
                                                       following=author).exists():
                return Response({'detail': 'Ошибка подписки'}, status=400)
            Follow.objects.create(user=user, following=author)
            serializer = self.get_serializer(author,
                                             context={'request': request})
            return Response(serializer.data, status=201)

        # DELETE
        deleted, _ = Follow.objects.filter(user=user,
                                           following=author).delete()
        if not deleted:
            return Response({'detail': 'Вы не были подписаны'}, status=400)
        return Response(status=204)

    @action(
        detail=False, methods=['GET'],
        url_path='subscriptions',
        permission_classes=[IsAuthenticated],
    )
    def subscriptions(self, request):
        """GET /api/users/subscriptions/  — мои подписки с пагинацией"""
        user = request.user
        follows = Follow.objects.filter(user=user).values_list(
            'following',flat=True
        )
        qs = User.objects.filter(pk__in=follows)
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        # на случай, если пагинация выключена
        serializer = UserWithRecipesSerializer(
            qs, many=True, context={'request': request}
        )
        return Response(serializer.data)

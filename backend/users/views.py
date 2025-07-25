from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework import (
    viewsets, permissions)
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User, Follow
from .serializers import UserRegistrationSerializer, UserSerializer, \
    AvatarSerializer


class CustomUserViewSet(UserViewSet):
    lookup_field = 'pk'
    serializer_class = UserSerializer
    queryset = User.objects.all()

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
            # возвращаем текущий URL аватара
            return Response(
                {'avatar': user.avatar.url if user.avatar else None})

        if request.method == 'PUT':
            serializer = AvatarSerializer(user, data=request.data,
                                          partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

            # DELETE
        user.avatar = None
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        url_path='me',
        methods=['GET', 'PATCH'],
        permission_classes=[permissions.IsAuthenticated, ],
    )
    def me_url(self, request):
        user = request.user
        if request.method == 'PATCH':
            serializer = self.get_serializer(user, data=request.data,
                                             partial=True)
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
        POST   /api/users/{pk}/subscribe/   — подписаться на пользователя pk
        DELETE /api/users/{pk}/subscribe/   — отписаться от пользователя pk
        """
        author = get_object_or_404(User, pk=pk)
        user = request.user

        # Показываем только одного и того же человека,
        # и нельзя подписаться на себя
        if author == user:
            return Response(
                {"detail": "Нельзя подписаться на самого себя."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.method == 'POST':
            # Если уже подписаны — ошибка
            if Follow.objects.filter(user=user, following=author).exists():
                return Response(
                    {"detail": "Уже подписаны."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            # Иначе создаём подписку
            Follow.objects.create(user=user, following=author)
            # Возвращаем детали автора, чтобы фронт сразу обновил UI
            serializer = self.get_serializer(author,
                                             context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        # DELETE
        deleted, _ = Follow.objects.filter(user=user,
                                           following=author).delete()
        if not deleted:
            return Response(
                {"detail": "Вы не были подписаны."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['GET'],
        url_path='subscriptions',
        permission_classes=[IsAuthenticated],
    )
    def subscriptions(self, request):
        """
        GET /api/users/subscriptions/ — список пользователей, на которых вы подписаны
        """
        user = request.user
        follows = Follow.objects.filter(user=user).values_list('following',
                                                               flat=True)
        queryset = User.objects.filter(pk__in=follows)
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(page, many=True,
                                         context={'request': request})
        return self.get_paginated_response(serializer.data)


class SignUpViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

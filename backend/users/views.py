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
    AvatarSerializer, UserWithRecipesSerializer


class CustomUserViewSet(UserViewSet):
    lookup_field = 'pk'
    serializer_class = UserSerializer
    queryset = User.objects.all()

    def get_serializer_class(self):
        # когда вызывается /api/users/subscriptions/ или /api/users/{pk}/subscribe/
        # — отдаём расширенный сериализатор с рецептами
        if self.action in ('retrieve', 'subscriptions', 'subscribe'):
            return UserWithRecipesSerializer
        # иначе — обычный
        return UserSerializer

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

            # на всякий случай, если придёт HEAD или другой метод:
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
            # возвращаем подробный профиль автора сразу же с его рецептами
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
        detail=False,
        methods=['GET'],
        url_path='subscriptions',
        permission_classes=[IsAuthenticated],
        pagination_class=None,  # убираем DRF-пагинацию
    )
    def subscriptions(self, request):
        """
        GET /api/users/subscriptions/ — мои подписки, сразу список UserWithRecipes
        """
        user = request.user
        follows = Follow.objects.filter(user=user) \
            .values_list('following', flat=True)
        qs = User.objects.filter(pk__in=follows)
        serializer = UserWithRecipesSerializer(
            qs, many=True, context={'request': request}
        )
        return Response(serializer.data)


class SignUpViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

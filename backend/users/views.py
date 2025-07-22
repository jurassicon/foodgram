from rest_framework import (
    viewsets, permissions, status)
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from .models import User
from .permissions import IsSupervisionOrAdmin
from .serializers import UserRegistrationSerializer, UserSerializer, AvatarSerializer


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = (
        permissions.IsAuthenticated,
        IsSupervisionOrAdmin,
    )
    lookup_field = 'username'

    search_fields = ('username',)
    http_method_names = ['get', 'post', 'put',
                         'patch', 'delete']
    serializer_class = UserSerializer

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
        detail=False,
        methods=['put'],
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated, ],
        parser_classes=[MultiPartParser],
    )
    def avatar(self, request):
        """
        PUT /api/users/me/avatar/ — загрузить новый аватар
        """
        serializer = AvatarSerializer(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class SignUpViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

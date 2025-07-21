from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import (
    generics, viewsets, permissions, status)
from .models import User
from .permissions import IsSupervisionOrAdmin
from .serializers import UserRegistrationSerializer, \
    ConfirmationCodeTokenSerializer, UserSerializer
from rest_framework import serializers


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = (
        permissions.IsAuthenticated,
        IsSupervisionOrAdmin,
    )
    lookup_field = 'username'

    search_fields = ('username',)
    http_method_names = ['get', 'post',
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
            serializer.save(role=user.role)
            return Response(serializer.data, status=status.HTTP_200_OK)
        serializer = self.get_serializer(user, many=False)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SignUpViewSet(viewsets.ViewSet):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username',
                  'email', 'avatar', 'password')

    def create(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConfirmationCodeTokenView(generics.GenericAPIView):
    serializer_class = ConfirmationCodeTokenSerializer

    def post(self, request, *args, **kwargs):
        serializer = ConfirmationCodeTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            serializer.validated_data, status=status.HTTP_200_OK)

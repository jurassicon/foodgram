from rest_framework import mixins, viewsets, filters

from users.permissions import IsSupervisionOrAdminOrReadOnly


class ListCreateRetrieveDestroyViewSet(
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    """
    Базовый ViewSet для «справочников» с полями name, slug и CRUD:
    list, create, retrieve запрещён, destroy.
    """
    filter_backends = (filters.SearchFilter,)
    lookup_field = 'slug'
    search_fields = ('name',)
    permission_classes = (IsSupervisionOrAdminOrReadOnly,)

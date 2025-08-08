from rest_framework.pagination import PageNumberPagination

from config import settings


class RecipesPagination(PageNumberPagination):
    page_size = settings.RECIPES_PER_PAGE
    page_size_query_param = 'limit'

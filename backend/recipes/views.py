from django.shortcuts import render
from rest_framework import viewsets


# Create your views here.
class RecipeViewSet(viewsets.ViewSet):
    pass

class IngredientViewSet(viewsets.ViewSet):
    pass

class RecipeIngredientViewSet(viewsets.ViewSet):
    pass

class TagViewSet(viewsets.ViewSet):
    pass
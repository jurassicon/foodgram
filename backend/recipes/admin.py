from django.contrib import admin

from users.models import User
from .models import Recipe, Ingredient, Tag, RecipeIngredient

admin.site.register(Tag)
admin.site.register(User)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1  # сколько пустых строк сразу показывать
    autocomplete_fields = ('ingredient',)  # поиск по готовому списку


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = (RecipeIngredientInline,)
    list_display = ('name', 'cooking_time')
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)

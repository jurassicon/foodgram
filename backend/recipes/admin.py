from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Count

from .models import Ingredient, Recipe, RecipeIngredient, Tag

User = get_user_model()

class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 0
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = (RecipeIngredientInline,)
    list_display = (
        'name',
        'author_name',
        'favorites_count',
        'pub_date',
        'cooking_time',
    )
    list_display_links = ('name',)
    search_fields = (
        'name',
        'author__username',
        'author__first_name',
        'author__last_name',
    )
    list_filter = ('tags',)
    readonly_fields = ('favorites_count',)
    fieldsets = (
        (None, {
            'fields': (
                'name',
                'author',
                'text',
                'image',
                'cooking_time',
                'tags',
                'favorites_count',
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(favorites_count=Count('favorites'))

    @admin.display(description='Автор')
    def author_name(self, obj):
        first = obj.author.first_name or ''
        last = obj.author.last_name or ''
        return f'{first} {last}'.strip() or obj.author.username

    @admin.display(description='Добавлений в избранное',
                   ordering='favorites_count')
    def favorites_count(self, obj):
        return obj.favorites_count


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ('name', 'slug')
    search_fields = ('name',)
    list_editable = ('slug',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name')
    search_fields = ('username', 'email',)
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    readonly_fields = ('last_login', 'date_joined')


admin.site.empty_value_display = 'Не задано'
admin.site.unregister(Group)
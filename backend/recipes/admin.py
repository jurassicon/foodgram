from django.contrib import admin

from users.models import User  # если нужно
from .models import Recipe, Ingredient, Tag, RecipeIngredient, Favourites


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1


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

    @admin.display(description='Автор')
    def author_name(self, obj):
        first = obj.author.first_name or ''
        last = obj.author.last_name or ''
        return f'{first} {last}'.strip() or obj.author.username

    @admin.display(description='Добавлений в избранное',
                   ordering='favourites__count')
    def favorites_count(self, obj):
        return Favourites.objects.filter(recipe=obj).count()


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    search_fields = ('name',)
    list_editable = ('slug',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)


admin.site.register(User)
admin.site.empty_value_display = 'Не задано'

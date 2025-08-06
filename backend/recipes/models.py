from datetime import datetime

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint

from recipes.constants import (
    CHARFIELD_MAX_LENGTH_LARGE,
    DEFAULT_CHARFIELD_MAX_LENGTH,
    NAME_MAX_LENGTH,
    TAG_NAME_MAX_LENGTH, TAG_SLUG_MAX_LENGTH, COOKING_TIME_MIN_VALUE,
    AMOUNT_TIME_MIN_VALUE,
)
from recipes.utils import get_short_string


class Tag(models.Model):
    name = models.CharField(
        'Название', max_length=TAG_NAME_MAX_LENGTH, unique=True,
        help_text='Дайте короткое название тэгу',
    )
    slug = models.SlugField(
        max_length=TAG_SLUG_MAX_LENGTH, unique=True,
        help_text=(
            'Укажите адрес тэга. Используйте только '
            'латиницу, цифры, дефисы и знаки подчёркивания')
    )

    class Meta:
        default_related_name = 'tags'
        verbose_name = 'тэг'
        verbose_name_plural = 'Тэги'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        'Название', max_length=NAME_MAX_LENGTH,
        help_text='Дайте короткое название рецепту'
    )
    text = models.TextField(
        'Текст', help_text='Добавьте подробностей',
    )
    image = models.ImageField(
        verbose_name='Иллюстрация', upload_to='recipes/images/'
    )
    ingredients = models.ManyToManyField(
        'Ingredient',
        through='RecipeIngredient',
        related_name='recipes',
        help_text='Список объектов {"id": ингредиент, "amount": количество}'
    )
    tags = models.ManyToManyField(
        Tag, verbose_name='Тэги', related_name='tag',
        help_text='Список ID тегов'
    )
    cooking_time = models.PositiveIntegerField(
        'Время приготовления',
        validators=[MinValueValidator(COOKING_TIME_MIN_VALUE)],
        help_text='Добавьте время приготовления в минутах',
    )
    pub_date = models.DateTimeField(
        'Дата публикации', auto_now_add=True
    )
    short_url = models.CharField(
        max_length=DEFAULT_CHARFIELD_MAX_LENGTH,
        unique=True,
        editable=False,
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        default_related_name = 'recipes'
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-pub_date',)

    def __str__(self):
        return get_short_string(self.name)

    def save(self, *args, **kwargs):
        if not self.short_url:
            from sqids import Sqids
            timestamp = round(datetime.now().timestamp() * 1000)
            code = Sqids().encode(
                [timestamp, self.author_id, self.cooking_time])
            self.short_url = code
        super().save(*args, **kwargs)


class Ingredient(models.Model):
    name = models.CharField(
        'Название', max_length=CHARFIELD_MAX_LENGTH_LARGE,
        unique=True, help_text='Дайте короткое название рецепту',
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=DEFAULT_CHARFIELD_MAX_LENGTH,
        help_text='Единица измерения (г, мл, шт и т.п.)',
    )

    class Meta:
        default_related_name = 'ingredients'
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = (
            UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_&_measurement_unit',
            ),
        )
        ordering = ('name',)

    def __str__(self):
        return get_short_string(self.name)


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(
        'Recipe', on_delete=models.CASCADE,
        related_name='recipe_ingredients', help_text='Рецепт'
    )
    ingredient = models.ForeignKey(
        'Ingredient', on_delete=models.CASCADE, help_text='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        validators=[MinValueValidator(AMOUNT_TIME_MIN_VALUE)],
        help_text='Количество ингредиента целое, ≥1'
    )

    class Meta:
        unique_together = ('recipe', 'ingredient')
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        ordering = ('recipe', 'ingredient')

    def __str__(self):
        return (f'{self.ingredient.name}: {self.amount} '
                f'{self.ingredient.measurement_unit}')


class FavouritesAndShoppingList(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='%(model_name)s_user'
    )
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='%(model_name)s'
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_%(app_label)s_%(class)s_user_recipe',
            ),
        ]


class Favourites(FavouritesAndShoppingList):
    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'
        ordering = ('-id',)

    def __str__(self):
        return f'Рецепт {self.recipe} в избранном у {self.user.username}'

    def clean(self):
        if Favourites.objects.filter(
                user=self.user,
                recipe=self.recipe
        ).exists():
            raise ValidationError({
                'recipe': 'Рецепт уже в избранном.'
            })


class ShoppingList(FavouritesAndShoppingList):
    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзина'
        default_related_name = 'shopping_recipe'
        ordering = ('user', 'recipe')

    def __str__(self):
        return f'Рецепт {self.recipe} в списке покупок {self.user.username}'

    def clean(self):
        if ShoppingList.objects.filter(
                user=self.user,
                recipe=self.recipe
        ).exists():
            raise ValidationError({
                'recipe': 'Рецепт уже в списке покупок.'
            })

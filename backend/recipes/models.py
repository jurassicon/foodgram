from django.core.exceptions import ValidationError
from sqids import Sqids
from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint
from django.utils.text import slugify


User = get_user_model()


def get_short_string(input_string, length=40, suffix='...'):
    if len(input_string) <= length:
        return input_string
    return input_string[:length] + suffix


class Tag(models.Model):
    name = models.CharField(
        'Название', max_length=32, unique=True, blank=False,
        help_text='Дайте короткое название тэгу',
    )
    slug = models.SlugField(
        'Уникальный адрес для тэга', max_length=32, unique=True,
        blank=True, null=True,
        help_text=(
            'Укажите адрес тэга. Используйте только '
                               'латиницу, цифры, дефисы и знаки подчёркивания')
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            max_slug_length = self._meta.get_field('slug').max_length
            self.slug = slugify(self.name)[:max_slug_length]
        super().save(*args, **kwargs)

    class Meta:
        default_related_name = 'tags'
        verbose_name = 'тэг'
        verbose_name_plural = 'Тэги'

    def __str__(self):
        return get_short_string(self.name)


class Recipe(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    name = models.CharField(
        'Название', max_length=256,
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
        validators=[MinValueValidator(1)],
        help_text='Добавьте время приготовления в минутах',
    )
    pub_date = models.DateTimeField(
        'Дата публикации', auto_now_add=True
    )
    short_url = models.CharField(
        max_length=64,
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

    #def __init__(self, *args, **kwargs):
    #    super().__init__(*args, **kwargs)
    #    self.short_url = None

    def __str__(self):
        return get_short_string(self.name)

    def save(self, *args, **kwargs):
        if not self.short_url:
            from datetime import datetime
            from sqids import Sqids
            timestamp = round(datetime.now().timestamp() * 1000)
            code = Sqids().encode(
                [timestamp, self.author_id, self.cooking_time])
            self.short_url = code
        super().save(*args, **kwargs)


class Ingredient(models.Model):
    name = models.CharField(
        'Название', max_length=128,
        unique=True,  help_text='Дайте короткое название рецепту',
    )
    measurement_unit = models.CharField(
        'Единица измерения',
        max_length=64,
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
        validators=[MinValueValidator(1)],
        help_text='Количество ингредиента целое, ≥1'
    )

    class Meta:
        unique_together = ('recipe', 'ingredient')
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'

    def __str__(self):
        return (f'{self.ingredient.name}: {self.amount} '
                f'{self.ingredient.measurement_unit}')


class FavouritesAndShoppingList(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class Favourites(FavouritesAndShoppingList):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favourites'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'
        constraints = (
            UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_and_recipe_in_Favourites',
            ),
        )

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
        constraints = (
            UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_and_recipe_in_ShoppingList',
            ),
        )

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
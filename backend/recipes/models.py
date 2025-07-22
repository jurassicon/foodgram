from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import slugify


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
        get_user_model(),
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

    class Meta:
        default_related_name = 'recipes'
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return get_short_string(self.name)


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

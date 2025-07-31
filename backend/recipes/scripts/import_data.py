#!/usr/bin/env python3
import os
import sys

import django
import pandas as pd


def main():
    # настраиваем путь и Django
    this_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(this_dir, '..', '..'))
    sys.path.insert(0, project_root)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

    # теперь безопасно импортируем модели
    from recipes.models import Ingredient, Tag

    data_dir = os.path.join(this_dir, 'csv_data')
    ingredients_csv = os.path.join(data_dir, 'ingredients.csv')
    tags_csv = os.path.join(data_dir, 'tags.csv')

    # 1) Ингредиенты
    Ingredient.objects.all().delete()
    if os.path.exists(ingredients_csv):
        df_ing = pd.read_csv(
            ingredients_csv,
            header=None,
            names=['name', 'measurement_unit'],
        )
        objs = [
            Ingredient(
                name=row['name'],
                measurement_unit=row['measurement_unit'],
            )
            for _, row in df_ing.iterrows()
        ]
        Ingredient.objects.bulk_create(objs)
        print(f'Импортировано {len(objs)} ингредиентов')
    else:
        print(f'Файл не найден: {ingredients_csv}')

    # 2) Теги
    print('Удаляю старые теги…')
    Tag.objects.all().delete()

    if not os.path.exists(tags_csv):
        print(f'Файл не найден: {tags_csv}')
    else:
        df_tags = pd.read_csv(
            tags_csv,
            sep=';',
            header=None,
            names=['name', 'slug'],
            dtype=str,
        )
        # чистим пробелы и убираем пустые/дубликаты
        df_tags['slug'] = df_tags['slug'].str.strip()
        df_tags = df_tags[df_tags['slug'].notna()]
        df_tags = df_tags.drop_duplicates('slug')

        tag_objs = [
            Tag(name=row['name'], slug=row['slug'])
            for _, row in df_tags.iterrows()
        ]
        if tag_objs:
            Tag.objects.bulk_create(tag_objs)
        print(f'Импортировано {len(tag_objs)} тегов')


if __name__ == '__main__':
    main()

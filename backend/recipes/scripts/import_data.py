import os, sys, django, pandas as pd

THIS_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from recipes.models import Ingredient, Tag

DATA_DIR        = os.path.join(THIS_DIR, 'csv_data')
ingredients_csv = os.path.join(DATA_DIR, 'ingredients.csv')
tags_csv        = os.path.join(DATA_DIR, 'tags.csv')


Ingredient.objects.all().delete()
if os.path.exists(ingredients_csv):
    df_ing = pd.read_csv(
        ingredients_csv, header=None,
        names=['name','measurement_unit']
    )
    objs = [
        Ingredient(name=r['name'], measurement_unit=r['measurement_unit'])
        for _, r in df_ing.iterrows()
    ]
    Ingredient.objects.bulk_create(objs)
    print(f"Импортировано {len(objs)} ингредиентов")
else:
    print(f"Файл не найден: {ingredients_csv}")

print("Удаляю старые теги…")
Tag.objects.all().delete()

if not os.path.exists(tags_csv):
    print(f"Файл не найден: {tags_csv}")
else:
    df_tags = pd.read_csv(
        tags_csv,
        sep=';',
        header=None,
        names=['name', 'slug'],
        dtype=str,
    )
    df_tags = df_tags.dropna(subset=['slug']).drop_duplicates(subset=['slug'])
    tag_objs = [
        Tag(name=row['name'], slug=row['slug'])
        for _, row in df_tags.iterrows()
    ]
    if tag_objs:
        Tag.objects.bulk_create(tag_objs)
    print(f"Импортировано {len(tag_objs)} тегов")

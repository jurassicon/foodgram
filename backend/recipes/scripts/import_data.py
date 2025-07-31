import os
import sys

import django
import pandas as pd

from recipes.models import Ingredient, Tag

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

Ingredient.objects.all().delete()

DATA_DIR = os.path.join(THIS_DIR, 'csv_data')
csv_path = os.path.join(DATA_DIR, 'ingredients.csv', 'tags.csv')
df = pd.read_csv(csv_path, header=None, names=['name', 'measurement_unit'])

objs = [Ingredient(name=r['name'], measurement_unit=r['measurement_unit'])
        for _, r in df.iterrows()]
Ingredient.objects.bulk_create(objs)

print(f"Импортировано {len(objs)} ингредиентов")

print("Удаляю старые теги…")
Tag.objects.all().delete()

tags_csv = os.path.join(DATA_DIR, 'tags.csv')
if not os.path.exists(tags_csv):
    print(f"⚠ Файл tags.csv не найден в {DATA_DIR}")
else:
    df_tags = pd.read_csv(tags_csv, header=None, names=['name','slug'])

    objs = [
        Tag(name=row['name'], slug=row['slug'])
        for _, row in df_tags.iterrows()
    ]
    Tag.objects.bulk_create(objs)
    print(f"Импортировано {len(objs)} тегов")
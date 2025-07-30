#!/usr/bin/env python3
import os, sys, django, pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))
sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from recipes.models import Ingredient

Ingredient.objects.all().delete()

DATA_DIR = os.path.join(THIS_DIR, 'csv_data')
csv_path = os.path.join(DATA_DIR, 'ingredients.csv')
df = pd.read_csv(csv_path, header=None, names=['name','measurement_unit'])

objs = [Ingredient(name=r['name'], measurement_unit=r['measurement_unit'])
        for _, r in df.iterrows()]
Ingredient.objects.bulk_create(objs)

print(f"Импортировано {len(objs)} ингредиентов")

#!/usr/bin/env python3
import os
import sqlite3
import sys

import django
import pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))

PROJECT_ROOT = os.path.abspath(os.path.join(THIS_DIR, '..', '..'))

sys.path.insert(0, PROJECT_ROOT)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

django.setup()

DB_PATH = os.path.join(PROJECT_ROOT, 'db.sqlite3')
DATA_DIR = os.path.join(THIS_DIR, 'csv_data')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]
print("Таблицы в БД:", tables)

to_clear = [
    'recipes_ingredient',
]
for tbl in to_clear:
    if tbl in tables:
        print(f"Удаляю данные из {tbl}…")
        conn.execute(f"DELETE FROM {tbl};")
    else:
        print(f"⚠ Таблица {tbl} не найдена, пропускаю.")
conn.commit()

mappings = [
    ('ingredients.csv', 'recipes_ingredient'),
]

imported_counts = {}

for filename, table in mappings:
    if table not in tables:
        print(f"Пропускаю {filename}: таблицы {table} нет в БД.")
        continue
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        print(f"Файл {filename} не найден в {DATA_DIR}.")
        continue
    print(f"Загружаю {filename} -> {table}")
    df = pd.read_csv(
        path, header=None, names=['name', 'measurement_unit']
    )
    df.to_sql(table, conn, if_exists='append', index=False)

    imported_counts[table] = len(df)
    print(f"👍 {len(df)} строк импортировано в таблицу «{table}»")

conn.close()

print("\n=== Отчёт по импорту данных ===")
total = 0
for table, count in imported_counts.items():
    print(f" {table}: {count} строк")
    total += count
print(f"Всего строк импортировано: {total}")

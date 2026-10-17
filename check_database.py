
import sqlite3

connection = sqlite3.connect("tasks.db")
cursor = connection.cursor()

print("ТАБЛИЦЫ В БАЗЕ ДАННЫХ:")

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""")

for table in cursor.fetchall():
    print("-", table[0])

print("\nСОХРАНЁННЫЕ ЗАДАЧИ:")

cursor.execute("""
    SELECT id, user_id, title, category, deadline, is_completed
    FROM tasks
    ORDER BY id
""")

tasks = cursor.fetchall()

if tasks:
    for task in tasks:
        print(task)
else:
    print("Задач пока нет")

connection.close()

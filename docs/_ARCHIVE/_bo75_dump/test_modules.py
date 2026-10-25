"""Проверка модулей БО 7.2"""
import db
from modules.objects import create_object, get_all_objects
from modules.tasks import create_task, get_tasks_by_object
from modules.finance import add_expense, get_finance_summary

# 1. Инициализация базы
db.init_db()

# 2. Создаём объект
oid = create_object("Тестовый объект", budget=100000)
print(f"✅ Создан объект ID: {oid}")

# 3. Создаём задачу
tid = create_task(oid, "Проверить работу", priority="high")
print(f"✅ Создана задача ID: {tid}")

# 4. Добавляем расход
add_expense(oid, 5000, "материалы")
print(f"✅ Расход добавлен")

# 5. Проверяем финансы
fin = get_finance_summary(oid)
print(f"✅ Финансы: {fin}")

# 6. Список объектов
objs = get_all_objects()
print(f"✅ Всего объектов: {len(objs)}")

# 7. Задачи объекта
tasks = get_tasks_by_object(oid)
print(f"✅ Задач у объекта: {len(tasks)}")

print("\n🎉 ВСЕ МОДУЛИ РАБОТАЮТ!")
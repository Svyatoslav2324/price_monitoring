from app.database import engine
from sqlalchemy import text

print("Внимание! Удаляю все таблицы и очищаю схему...")

with engine.connect() as conn:
    # Это "ядерный" вариант: удаляет вообще всё в схеме public
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.execute(text("CREATE SCHEMA public;"))
    conn.commit()

print("База данных полностью очищена. Можно создавать таблицы заново.")
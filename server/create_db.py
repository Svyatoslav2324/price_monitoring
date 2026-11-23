import sys
import os

# Добавляем текущую папку в пути поиска Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base, SessionLocal
from app import models

def init_db():
    print("1. Создаю таблицы...")
    Base.metadata.create_all(bind=engine)
    print("   Таблицы успешно созданы!")

    print("2. Добавляю базовые маркетплейсы...")
    db = SessionLocal()
    try:
        # Список маркетплейсов, которые должны быть в системе
        default_marketplaces = ["Ozon", "Wildberries", "AliExpress", "Yandex Market"]
        
        for name in default_marketplaces:
            # Проверяем, есть ли уже такой маркетплейс в базе
            existing = db.query(models.Marketplace).filter(models.Marketplace.name == name).first()
            if not existing:
                new_marketplace = models.Marketplace(name=name)
                db.add(new_marketplace)
                print(f"   + Добавлен: {name}")
            else:
                print(f"   - Уже существует: {name}")
        
        db.commit()
        print("   Маркетплейсы успешно добавлены!")
    except Exception as e:
        print(f"   Ошибка при добавлении: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("\nГотово! База данных инициализирована.")
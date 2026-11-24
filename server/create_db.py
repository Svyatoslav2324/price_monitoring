from sqlalchemy import text
import sys
import os

# Добавляем текущую папку в пути поиска Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, Base, SessionLocal
from app import models
from app.marketplaces import DOMAINS

def init_db():
    print("1. Создаю таблицы...")
    Base.metadata.create_all(bind=engine)
    with engine.begin() as db:
        db.execute(text("ALTER TABLE links ADD COLUMN IF NOT EXISTS price_status VARCHAR(32)"))
    print("   Таблицы успешно созданы!")

    print("2. Добавляю базовые маркетплейсы...")
    db = SessionLocal()
    try:
        # Список маркетплейсов, которые должны быть в системе
        default_marketplaces = DOMAINS
        
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
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
    print("\nГотово! База данных инициализирована.")
from sqlalchemy.orm import Session
from . import models
from .security import get_password_hash # <-- Импортируем только функцию хеширования
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload
from typing import List
from datetime import timedelta

def create_user(db: Session, user_data: dict) -> models.Client:
    """Создает нового клиента в базе данных."""
    # Хешируем пароль (вызываем функцию из security.py)
    hashed_password = get_password_hash(user_data['password'])
    
    db_client = models.Client(
        login=user_data['login'],
        password_hash=hashed_password,
        balance=0
    )
    
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

def update_product_price(db: Session, product: models.Product, new_price: float) -> models.Product:
    """
    Обновляет текущую цену и пишет изменение в таблицу price_history.
    """
    product.current_price = new_price
    
    history_record = models.PriceHistory(
        product_id=product.id,
        price=new_price
    )
    
    db.add(history_record)
    db.commit()
    db.refresh(product) 
    
    return product


def create_group(db: Session, title: str, owner_id: int) -> models.Group:
    # по умолчанию группа приватная (is_verified=False) и принадлежит создателю
    db_group = models.Group(
        title=title,
        is_verified=False, 
        owner_id=owner_id
    )
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group

def add_link_to_group(db: Session, group_id: int, url: str, marketplace_id: int) -> models.Link:
    # 1. Ищем группу
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return None

    # 2. Ищем ссылку по URL
    link = db.query(models.Link).filter(models.Link.url == url).first()
    
    # 3. Если ссылки нет, создаем её
    if not link:
        link = models.Link(
            url=url, 
            marketplace_id=marketplace_id,
            # Ставим начальное время парсинга (например, сейчас + 60 минут)
            parse_interval=60,
            next_parse_at=func.now()
        )
        db.add(link)
        db.commit()
        db.refresh(link)

    # 4. Привязываем ссылку к группе (магия Many-to-Many)
    # Проверяем, нет ли уже такой связи, чтобы не было дублей
    if link not in group.links:
        group.links.append(link)
        db.commit()

    return link




def get_user_groups(db: Session, user_id: int) -> List[models.Group]:
    """
    Возвращает все группы, которые создал пользователь.
    """
    return db.query(models.Group).filter(models.Group.owner_id == user_id).all()

def get_group_with_links(db: Session, group_id: int) -> models.Group:
    """
    Возвращает группу вместе со всеми её ссылками.
    Использует joinedload, чтобы сделать это за ОДИН запрос.
    """
    return db.query(models.Group).options(
        joinedload(models.Group.links)
    ).filter(models.Group.id == group_id).first()




def recalculate_links_interval(db: Session, group_id: int):
    """
    Пересчитывает минимальный интервал парсинга для всех ссылок в группе.
    Вызывается при создании/изменении подписки.
    """
    # 1. Находим минимальный интервал опроса по подписке среди всех АКТИВНЫХ подписок на эту группу
    # Если подписок нет, вернется None
    min_interval = db.query(func.min(models.Subscription.interval))\
        .filter(
            models.Subscription.group_id == group_id,
            models.Subscription.status == 'active'
        ).scalar()

    # 2. Если подписок нет, ставим ссылкам дефолтный интервал (например, раз в сутки)
    if min_interval is None:
        min_interval = 1440 # 24 часа в минутах
    # Вообще лучше добавить отдельный статус, что группа не опрашивается,
    # тоесть что каждая ссылка группы не парсится

    # 3. Достаем группу и её ссылки
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    
    if group:
        # 4. Обновляем каждую ссылку
        for link in group.links:
            # Если интервал изменился, обновляем и время следующего парсинга
            if link.parse_interval != min_interval:
                link.parse_interval = min_interval
                link.next_parse_at = func.now() + timedelta(minutes=min_interval)
        
        db.commit()




def remove_link_from_group(db: Session, group_id: int, link_id: int) -> bool:
    """
    Удаляет связь между ссылкой и группой.
    Сама ссылка остается в базе (она может быть в других группах).
    """
    # 1. Находим группу
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        return False

    # 2. Находим ссылку
    link = db.query(models.Link).filter(models.Link.id == link_id).first()
    if not link:
        return False

    # 3. Проверяем, есть ли вообще такая связь
    if link not in group.links:
        return False

    # 4. Удаляем связь (SQLAlchemy сама удалит запись из group_links)
    group.links.remove(link)
    db.commit()
    
    return True


# ... (твои остальные функции) ...

def delete_group(db: Session, group_id: int, user_id: int) -> bool:
    """
    Удаляет группу пользователя.
    Ссылки не удаляются, удаляются только связи (каскадом базы).
    """
    # 1. Находим группу
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    
    if not group:
        return False
        
    # 2. Проверяем, что это группа этого пользователя
    if group.owner_id != user_id:
        return False

    # 3. Удаляем группу. 
    # Благодаря ondelete="CASCADE" в базе, 
    # автоматически удалятся записи из group_links и subscriptions.
    db.delete(group)
    db.commit()
    
    return True


def create_subscription(db: Session, user_id: int, group_id: int, interval: int) -> models.Subscription:
    # 1. Создаем подписку
    db_sub = models.Subscription(
        client_id=user_id,
        group_id=group_id,
        interval=interval,
        status="active"
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)

    # 2. Пересчитываем интервалы для ссылок в группе!
    recalculate_links_interval(db, group_id)

    return db_sub



# ... (твои остальные функции) ...

def get_user_subscriptions(db: Session, user_id: int):
    """Возвращает список всех подписок пользователя."""
    return db.query(models.Subscription).filter(
        models.Subscription.client_id == user_id
    ).all()

def delete_subscription(db: Session, subscription_id: int, user_id: int):
    """
    Удаляет подписку и пересчитывает интервалы для ссылок группы.
    """
    # 1. Находим подписку (только свою!)
    sub = db.query(models.Subscription).filter(
        models.Subscription.id == subscription_id,
        models.Subscription.client_id == user_id
    ).first()

    if not sub:
        return False

    group_id = sub.group_id
    
    # 2. Удаляем подписку
    db.delete(sub)
    db.commit()

    # 3. Пересчитываем интервалы для ссылок в этой группе
    recalculate_links_interval(db, group_id)
    
    return True


def get_link_price_history(db: Session, link_id: int, limit: int = 100, offset: int = 0):
    """
    Возвращает историю цен для конкретной ссылки.
    По умолчанию отдает последние 100 записей (от старых к новым).
    """
    return db.query(models.PriceHistory)\
        .filter(models.PriceHistory.link_id == link_id)\
        .order_by(models.PriceHistory.date.asc())\
        .offset(offset)\
        .limit(limit)\
        .all()
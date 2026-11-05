from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, crud
from ..dependencies import get_db, get_current_user
from typing import List

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])

@router.post("/", response_model=schemas.SubscriptionResponse, status_code=201)
def subscribe_to_group(
    sub_data: schemas.SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    # 1. Проверяем, существует ли группа
    group = db.query(models.Group).filter(models.Group.id == sub_data.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
        
    # 2. Проверяем, не подписан ли уже пользователь на эту группу
    existing_sub = db.query(models.Subscription).filter(
        models.Subscription.client_id == current_user.id,
        models.Subscription.group_id == sub_data.group_id
    ).first()
    
    if existing_sub:
        raise HTTPException(status_code=400, detail="Вы уже подписаны на эту группу")

    # 3. Создаем подписку (и пересчитываем интервалы)
    new_sub = crud.create_subscription(
        db, 
        user_id=current_user.id, 
        group_id=sub_data.group_id, 
        interval=sub_data.interval
    )
    return new_sub


@router.get("/", response_model=List[schemas.SubscriptionResponse])
def get_my_subscriptions(
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    """Получить список всех моих подписок."""
    return crud.get_user_subscriptions(db, user_id=current_user.id)

@router.delete("/{subscription_id}", status_code=204)
def unsubscribe(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    """Отписаться от группы."""
    success = crud.delete_subscription(db, subscription_id=subscription_id, user_id=current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Подписка не найдена")
    
    return None # 204 No Content означает "Успешно, но отвечать нечем"
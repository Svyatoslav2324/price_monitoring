from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, crud
from ..dependencies import get_db, get_current_user

router = APIRouter(prefix="/links", tags=["Links"])

@router.get("/{link_id}/history", response_model=List[schemas.PriceHistoryResponse])
def get_price_history(
    link_id: int,
    limit: int = Query(100, le=500, description="Сколько точек вернуть (макс 500)"),
    offset: int = Query(0, description="Смещение для пагинации"),
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    """
    Получить историю цен для конкретной ссылки.
    Возвращает точки (дата, цена), отсортированные от старых к новым.
    """
    # 1. Проверяем, существует ли ссылка
    link = db.query(models.Link).filter(models.Link.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="Ссылка не найдена")

    # 2. (Опционально) Проверка прав: пользователь должен быть подписан на группу, где есть эта ссылка.
    # Пока разрешим смотреть всем авторизованным, чтобы не усложнять.
    
    # 3. Достаем историю
    history = crud.get_link_price_history(db, link_id=link_id, limit=limit, offset=offset)
    return history
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas, crud, database
from ..dependencies import get_db, get_current_user
from typing import List

router = APIRouter(prefix="/groups", tags=["Groups"])

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("", response_model=schemas.GroupResponse, status_code=201)
def create_group(
    group: schemas.GroupCreate, 
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    return crud.create_group(db, title=group.title, owner_id=current_user.id)

@router.post("/{group_id}/links", response_model=schemas.LinkResponse, status_code=201)
def add_link(
    group_id: int,
    link_data: schemas.LinkCreate,
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    # 1. Проверяем, существует ли группа и принадлежит ли она пользователю
    # (Пока разрешаем добавлять только в свои группы. Публичные добавим позже)
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы не можете изменять чужую группу")

    # 2. Проверяем, существует ли маркетплейс
    marketplace = db.query(models.Marketplace).filter(models.Marketplace.id == link_data.marketplace_id).first()
    if not marketplace:
        raise HTTPException(status_code=404, detail="Маркетплейс не найден")

    # 3. Вызываем нашу функцию
    new_link = crud.add_link_to_group(
        db, 
        group_id=group_id, 
        url=link_data.url, 
        marketplace_id=link_data.marketplace_id
    )
    
    return new_link


@router.get("/", response_model=List[schemas.GroupResponse])
def get_my_groups(
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    """
    Получить список всех групп, которые создал текущий пользователь.
    """
    return crud.get_user_groups(db, user_id=current_user.id)

@router.get("/{group_id}", response_model=schemas.GroupWithLinksResponse)
def get_group_details(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    """
    Получить группу со всеми её ссылками.
    """
    # 1. Достаем группу со ссылками
    group = crud.get_group_with_links(db, group_id=group_id)
    
    # 2. Проверяем, существует ли она
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
        
    # 3. Проверяем права доступа: 
    # Смотреть можно только свои группы (или публичные, но их пока нет)
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="У вас нет доступа к этой группе")
        
    return group


@router.delete("/{group_id}/links/{link_id}", status_code=204)
def remove_link(
    group_id: int,
    link_id: int,
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    """
    Удалить ссылку из группы.
    """
    # 1. Проверяем, существует ли группа и принадлежит ли она пользователю
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Группа не найдена")
    
    if group.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы не можете изменять чужую группу")

    # 2. Вызываем функцию удаления
    success = crud.remove_link_from_group(db, group_id=group_id, link_id=link_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Ссылка не найдена в этой группе")
    
    return None


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: models.Client = Depends(get_current_user)
):
    """
    Удалить группу.
    """
    success = crud.delete_group(db, group_id=group_id, user_id=current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Группа не найдена или у вас нет прав на её удаление")
    
    return None
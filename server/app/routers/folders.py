from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from ..dependencies import get_current_user, get_db
from ..models import Folder, FolderItem, Group, Link, Marketplace, Subscription

router = APIRouter(prefix="/folders", tags=["Folders"])


class FolderCreate(BaseModel):
    name: str = Field(max_length=80)
    marketplace_id: int


class Destination(BaseModel):
    folder_id: int | None


@router.get("")
def library(db: Session = Depends(get_db), user=Depends(get_current_user)):
    folders = db.query(Folder).filter_by(owner_id=user.id).order_by(Folder.name).all()
    items = db.query(FolderItem).filter_by(owner_id=user.id)
    return {"folders": [{"id": f.id, "name": f.name, "marketplace_id": f.marketplace_id} for f in folders],
            "items": {i.link_id: i.folder_id for i in items}}


@router.post("", status_code=201)
def create_folder(data: FolderCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    name = data.name.strip()
    if not name or not db.get(Marketplace, data.marketplace_id):
        raise HTTPException(400, "Проверьте название и маркетплейс")
    folder = db.execute(insert(Folder).values(owner_id=user.id, name=name, marketplace_id=data.marketplace_id)
                        .on_conflict_do_nothing().returning(Folder.id)).scalar()
    if folder is None:
        raise HTTPException(409, "Группа с таким названием уже существует")
    db.commit()
    return {"id": folder}


@router.put("/items/{link_id}", status_code=204)
def move_item(link_id: int, data: Destination, db: Session = Depends(get_db), user=Depends(get_current_user)):
    link = db.query(Link).join(Link.groups).join(Group.subscriptions).filter(
        Link.id == link_id, Subscription.client_id == user.id).first()
    if link is None:
        raise HTTPException(404, "Товар отсутствует в ваших отслеживаниях")
    if data.folder_id is None:
        db.query(FolderItem).filter_by(owner_id=user.id, link_id=link_id).delete()
    else:
        folder = db.query(Folder).filter_by(id=data.folder_id, owner_id=user.id,
                                           marketplace_id=link.marketplace_id).first()
        if folder is None:
            raise HTTPException(404, "Группа недоступна для этого товара")
        db.execute(insert(FolderItem).values(owner_id=user.id, link_id=link_id, folder_id=folder.id)
                   .on_conflict_do_update(index_elements=["owner_id", "link_id"], set_={"folder_id": folder.id}))
    db.commit()

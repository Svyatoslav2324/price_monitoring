from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from pydantic import BaseModel
from typing import Literal

from .. import models
from ..marketplaces import DOMAINS, marketplace_for
from ..dependencies import get_current_user, get_db
from ..order_sheet import MAX_BYTES, parse_sheet, template

router = APIRouter(prefix="/imports", tags=["Imports"])


@router.get("/template.xlsx")
def download_template():
    return Response(template(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": 'attachment; filename="marketplace-links.xlsx"'})


@router.post("/orders")
def import_orders(file: UploadFile, db: Session = Depends(get_db), user=Depends(get_current_user)):
    try:
        orders = parse_sheet(file.file.read(MAX_BYTES + 1))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return save_orders(db, user, orders)


class OrderInput(BaseModel):
    url: str
    interval: Literal[60, 360, 1440]


@router.post("/order")
def add_order(order: OrderInput, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return save_orders(db, user, {order.url.strip(): order.interval})


@router.get("/marketplaces")
def marketplaces(db: Session = Depends(get_db)):
    return [{"id": market.id, "name": market.name, "domain": DOMAINS[market.name]}
            for market in db.query(models.Marketplace).order_by(models.Marketplace.id)
            if market.name in DOMAINS]


def save_orders(db, user, orders):
    ids = {market["name"]: market["id"] for market in marketplaces(db)}
    added = 0
    for url, interval in sorted(orders.items()):
        try:
            market_id = ids[marketplace_for(url)]
        except (KeyError, ValueError) as exc:
            raise HTTPException(400, "Проверьте ссылку и доступность маркетплейса") from exc
        db.execute(insert(models.Link).values(url=url, marketplace_id=market_id,
                   parse_interval=interval, next_parse_at=func.now()).on_conflict_do_nothing(index_elements=["url"]))
        link = db.query(models.Link).filter_by(url=url).with_for_update().one()
        existing = db.query(models.Subscription).join(models.Group).join(models.Group.links).filter(
            models.Link.id == link.id, models.Subscription.client_id == user.id).first()
        if existing:
            continue
        group = models.Group(title=url, owner_id=user.id, links=[link])
        db.add(models.Subscription(group=group, client_id=user.id, interval=interval, status="active"))
        link.next_parse_at = func.now()
        added += 1
    db.commit()
    return {"added": added, "existing": len(orders) - added}

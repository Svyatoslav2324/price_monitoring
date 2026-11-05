from pydantic import BaseModel
from datetime import datetime

class UserCreate(BaseModel):
    login: str
    password: str

class UserResponse(BaseModel):
    id: int
    login: str
    balance: float

    class Config:
        from_attributes = True # Позволяет Pydantic читать данные из объектов SQLAlchemy

class Token(BaseModel):
    access_token: str
    token_type: str



class GroupCreate(BaseModel):
    title: str

class GroupResponse(BaseModel):
    id: int
    title: str
    is_verified: bool
    owner_id: int | None # Может быть None, если группа публичная

    class Config:
        from_attributes = True



class LinkCreate(BaseModel):
    url: str
    marketplace_id: int

class LinkResponse(BaseModel):
    id: int
    url: str
    marketplace_id: int
    current_price: float | None
    last_parsed_at: datetime | None

    class Config:
        from_attributes = True

class GroupWithLinksResponse(BaseModel):
    id: int
    title: str
    is_verified: bool
    links: list[LinkResponse] = [] # Возвращаем список ссылок

    class Config:
        from_attributes = True


class SubscriptionCreate(BaseModel):
    group_id: int
    interval: int # 10, 30, 60 и т.д.

class SubscriptionResponse(BaseModel):
    id: int
    group_id: int
    interval: int
    status: str

    class Config:
        from_attributes = True



class SubscriptionResponse(BaseModel):
    id: int
    group_id: int
    interval: int
    status: str

    class Config:
        from_attributes = True





class PriceHistoryResponse(BaseModel):
    date: datetime
    price: float

    class Config:
        from_attributes = True
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime, BigInteger, Boolean, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# ==========================================
# СВЯЗУЮЩАЯ ТАБЛИЦА (Many-to-Many)
# ==========================================
# Нужна для связи "одна ссылка может быть в нескольких группах"
group_links = Table(
    'group_links',
    Base.metadata,
    Column('group_id', Integer, ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    Column('link_id', BigInteger, ForeignKey('links.id', ondelete='CASCADE'), primary_key=True)
)

# ==========================================
# ОСНОВНЫЕ МОДЕЛИ
# ==========================================

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True)
    login = Column(String(255), unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    balance = Column(Numeric(15, 2), default=0)
    
    subscriptions = relationship("Subscription", back_populates="client")
    # Связь с группами, которые создал пользователь (для будущей "мастерской")
    created_groups = relationship("Group", back_populates="owner")

class Marketplace(Base):
    __tablename__ = "marketplaces"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    
    links = relationship("Link", back_populates="marketplace")

class Group(Base):
    """
    Группа (Тайтл) для объединения предложений. 
    Например: "Смартфон VIVO версия 6.7".
    """
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True)
    
    # Флаг: True - создана админом (глобальный пул), False - создана юзером (приватная)
    is_verified = Column(Boolean, default=False, index=True)
    
    # Если группа приватная, здесь ID создателя. Если глобальная - NULL.
    owner_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=True)
    
    owner = relationship("Client", back_populates="created_groups")
    
    # Связь Many-to-Many со ссылками через таблицу group_links
    links = relationship("Link", secondary=group_links, back_populates="groups")
    
    # Связь с подписками
    subscriptions = relationship("Subscription", back_populates="group")

class Link(Base):
    """
    Конкретная ссылка на товар у конкретного продавца на маркетплейсе.
    """
    __tablename__ = "links"
    id = Column(BigInteger, primary_key=True)
    
    # Ссылка должна быть уникальной, чтобы не парсить одно и то же дважды
    url = Column(String(255), unique=True, index=True)
    marketplace_id = Column(Integer, ForeignKey("marketplaces.id", ondelete="CASCADE"))
    
    current_price = Column(Numeric(15, 2), nullable=True)
    
    # --- ПОЛЯ ДЛЯ ПЛАНИРОВЩИКА (ВОРКЕРА) ---
    # Как часто парсить эту ссылку (в минутах). Берется минимальный из всех групп.
    parse_interval = Column(Integer, default=60) 
    # Когда следующий раз идти на сайт
    next_parse_at = Column(DateTime(timezone=True), nullable=True, index=True)
    # Когда последний раз успешно спарсили (для отображения "Обновлено N минут назад")
    last_parsed_at = Column(DateTime(timezone=True), nullable=True)
    
    marketplace = relationship("Marketplace", back_populates="links")
    groups = relationship("Group", secondary=group_links, back_populates="links")
    price_history = relationship(
        "PriceHistory", 
        back_populates="link",
        order_by="desc(PriceHistory.date)"
    )

class PriceHistory(Base):
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True)
    link_id = Column(BigInteger, ForeignKey("links.id", ondelete="CASCADE"))
    price = Column(Numeric(15, 2))
    date = Column(DateTime(timezone=True), server_default=func.now())
    
    link = relationship("Link", back_populates="price_history")

class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True)
    
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"))
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"))
    
    # ИНТЕРВАЛ (в минутах), который выбрал пользователь для этой группы (10, 30, 60...)
    interval = Column(Integer, nullable=False, default=60) 
    
    # Когда последний раз отправляли уведомление (чтобы не спамить)
    last_notified_at = Column(DateTime(timezone=True), nullable=True)
    
    status = Column(String(255), default="active")
    
    client = relationship("Client", back_populates="subscriptions")
    group = relationship("Group", back_populates="subscriptions")
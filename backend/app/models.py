from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class InventoryStatus(str, Enum):
    received = "Received"
    iol = "IOL"
    missing = "Missing"
    damaged = "Damaged"
    resolved = "Resolved"
    stowed = "Stowed"


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asin: Mapped[str] = mapped_column(String(32), index=True)
    sku: Mapped[str] = mapped_column(String(80), index=True)
    lpn: Mapped[str] = mapped_column(String(80), index=True)
    tote_id: Mapped[str] = mapped_column(String(80), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    condition: Mapped[str] = mapped_column(String(40), index=True)
    location: Mapped[str] = mapped_column(String(80), index=True)
    department: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by: Mapped["User | None"] = relationship(back_populates="inventory_items")

    @property
    def created_by_username(self) -> str | None:
        return self.created_by.username if self.created_by else None


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="worker", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    inventory_items: Mapped[list[InventoryItem]] = relationship(back_populates="created_by")


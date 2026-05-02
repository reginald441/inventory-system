from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


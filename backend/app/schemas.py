from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StatusLiteral = Literal["Received", "IOL", "Missing", "Damaged", "Resolved", "Stowed"]
DepartmentLiteral = Literal["Receive", "IOL"]


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InventoryBase(BaseModel):
    asin: str = Field(min_length=1, max_length=32)
    sku: str = Field(min_length=1, max_length=80)
    lpn: str = Field(min_length=1, max_length=80)
    tote_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=0)
    condition: str = Field(min_length=1, max_length=40)
    location: str = Field(min_length=1, max_length=80)
    department: DepartmentLiteral
    status: StatusLiteral
    notes: str = Field(default="", max_length=2000)


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(InventoryBase):
    pass


class InventoryOut(InventoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class DashboardSummary(BaseModel):
    total_items: int
    total_units: int
    by_status: dict[str, int]
    by_department: dict[str, int]


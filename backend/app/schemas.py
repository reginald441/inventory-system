from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

StatusLiteral = Literal["Received", "IOL", "Missing", "Damaged", "Resolved", "Stowed"]
DepartmentLiteral = Literal["Receive", "IOL"]
RoleLiteral = Literal["admin", "worker"]


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(LoginRequest):
    pass


class UserRoleUpdate(BaseModel):
    role: RoleLiteral


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: RoleLiteral
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


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
    created_by_user_id: int | None = None
    created_by_username: str | None = None
    created_at: datetime
    updated_at: datetime


class DashboardSummary(BaseModel):
    total_items: int
    total_units: int
    by_status: dict[str, int]
    by_department: dict[str, int]


class ActivityPoint(BaseModel):
    date: str
    count: int


class ActiveUserSummary(BaseModel):
    username: str
    count: int


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    item_id: int | None
    user_id: int | None
    username: str
    old_value: str | None
    new_value: str | None
    created_at: datetime


class AnalyticsSummary(BaseModel):
    total_items: int
    total_units: int
    items_added_today: int
    items_added_this_week: int
    missing_count: int
    damaged_count: int
    resolved_count: int
    stowed_count: int
    status_counts: dict[str, int]
    department_counts: dict[str, int]
    recent_activity: list[AuditLogOut]
    top_active_users: list[ActiveUserSummary]
    daily_item_activity: list[ActivityPoint]


class InventoryHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_id: int
    status: str
    location: str
    notes: str
    changed_by_user_id: int | None
    created_at: datetime


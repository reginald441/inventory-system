import json
from datetime import datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, or_, text
from sqlalchemy.orm import Session

from .auth import authenticate_user, create_access_token, hash_password, require_admin, require_auth, require_worker_or_admin
from .database import Base, engine, get_db
from .models import AuditLog, InventoryHistory, InventoryItem, InventoryStatus, User
from .schemas import AnalyticsSummary, AuditLogOut, DashboardSummary, InventoryCreate, InventoryHistoryOut, InventoryOut, InventoryUpdate, LoginRequest, SignupRequest, TokenResponse, UserOut, UserRoleUpdate

Base.metadata.create_all(bind=engine)


def ensure_runtime_schema() -> None:
    inspector = inspect(engine)
    if "inventory_items" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("inventory_items")}
    if "created_by_user_id" not in columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE inventory_items ADD COLUMN created_by_user_id INTEGER"))


ensure_runtime_schema()

app = FastAPI(title="Warehouse Inventory Tracking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://inventory-system-seven-inky.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def item_snapshot(item: InventoryItem) -> dict[str, object]:
    return {
        "id": item.id,
        "asin": item.asin,
        "sku": item.sku,
        "lpn": item.lpn,
        "tote_id": item.tote_id,
        "quantity": item.quantity,
        "condition": item.condition,
        "location": item.location,
        "department": item.department,
        "status": item.status,
        "notes": item.notes,
    }


def dump_value(value: object) -> str:
    return json.dumps(value, default=str, sort_keys=True)


def add_audit_log(
    db: Session,
    *,
    action: str,
    user: User,
    item_id: int | None,
    old_value: object | None = None,
    new_value: object | None = None,
) -> None:
    db.add(
        AuditLog(
            action=action,
            item_id=item_id,
            user_id=user.id,
            username=user.username,
            old_value=dump_value(old_value) if old_value is not None else None,
            new_value=dump_value(new_value) if new_value is not None else None,
        )
    )


def add_history(db: Session, *, item: InventoryItem, user: User) -> None:
    db.add(
        InventoryHistory(
            item_id=item.id,
            status=item.status,
            location=item.location,
            notes=item.notes,
            changed_by_user_id=user.id,
        )
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user), user=UserOut.model_validate(user))


@app.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username is required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 8 characters")
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = User(username=username, password_hash=hash_password(payload.password), role="worker")
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=UserOut.model_validate(user))


@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(require_auth)):
    return current_user


@app.put("/users/{user_id}/role", response_model=UserOut)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@app.get("/dashboard", response_model=DashboardSummary)
def dashboard(_: User = Depends(require_worker_or_admin), db: Session = Depends(get_db)):
    total_items = db.query(func.count(InventoryItem.id)).scalar() or 0
    total_units = db.query(func.coalesce(func.sum(InventoryItem.quantity), 0)).scalar() or 0
    status_rows = db.query(InventoryItem.status, func.count(InventoryItem.id)).group_by(InventoryItem.status).all()
    department_rows = db.query(InventoryItem.department, func.count(InventoryItem.id)).group_by(InventoryItem.department).all()

    return DashboardSummary(
        total_items=total_items,
        total_units=total_units,
        by_status={status_name: count for status_name, count in status_rows},
        by_department={department: count for department, count in department_rows},
    )


@app.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(current_user: User = Depends(require_worker_or_admin), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = today_start - timedelta(days=today_start.weekday())
    seven_day_start = today_start - timedelta(days=6)

    total_items = db.query(func.count(InventoryItem.id)).scalar() or 0
    total_units = db.query(func.coalesce(func.sum(InventoryItem.quantity), 0)).scalar() or 0
    status_rows = db.query(InventoryItem.status, func.count(InventoryItem.id)).group_by(InventoryItem.status).all()
    department_rows = db.query(InventoryItem.department, func.count(InventoryItem.id)).group_by(InventoryItem.department).all()
    status_counts = {status_name: count for status_name, count in status_rows}
    department_counts = {department: count for department, count in department_rows}

    items_added_today = db.query(func.count(InventoryItem.id)).filter(InventoryItem.created_at >= today_start).scalar() or 0
    items_added_this_week = db.query(func.count(InventoryItem.id)).filter(InventoryItem.created_at >= week_start).scalar() or 0

    daily_rows = (
        db.query(func.date(InventoryItem.created_at), func.count(InventoryItem.id))
        .filter(InventoryItem.created_at >= seven_day_start)
        .group_by(func.date(InventoryItem.created_at))
        .all()
    )
    daily_counts = {str(day): count for day, count in daily_rows}
    daily_item_activity = [
        {"date": (seven_day_start + timedelta(days=offset)).date().isoformat(), "count": daily_counts.get((seven_day_start + timedelta(days=offset)).date().isoformat(), 0)}
        for offset in range(7)
    ]

    if current_user.role == "admin":
        recent_activity = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(10).all()
        user_rows = (
            db.query(AuditLog.username, func.count(AuditLog.id))
            .group_by(AuditLog.username)
            .order_by(func.count(AuditLog.id).desc())
            .limit(5)
            .all()
        )
        top_active_users = [{"username": username or "Unknown", "count": count} for username, count in user_rows]
    else:
        recent_activity = []
        top_active_users = []

    return AnalyticsSummary(
        total_items=total_items,
        total_units=total_units,
        items_added_today=items_added_today,
        items_added_this_week=items_added_this_week,
        missing_count=status_counts.get("Missing", 0),
        damaged_count=status_counts.get("Damaged", 0),
        resolved_count=status_counts.get("Resolved", 0),
        stowed_count=status_counts.get("Stowed", 0),
        status_counts=status_counts,
        department_counts=department_counts,
        recent_activity=recent_activity,
        top_active_users=top_active_users,
        daily_item_activity=daily_item_activity,
    )


@app.get("/items", response_model=list[InventoryOut])
def list_items(
    q: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    department: str | None = Query(default=None),
    condition: str | None = Query(default=None),
    location: str | None = Query(default=None),
    _: User = Depends(require_worker_or_admin),
    db: Session = Depends(get_db),
):
    query = db.query(InventoryItem)

    if q:
        pattern = f"%{q.strip()}%"
        query = query.filter(
            or_(
                InventoryItem.asin.ilike(pattern),
                InventoryItem.sku.ilike(pattern),
                InventoryItem.lpn.ilike(pattern),
                InventoryItem.tote_id.ilike(pattern),
                InventoryItem.condition.ilike(pattern),
                InventoryItem.location.ilike(pattern),
                InventoryItem.department.ilike(pattern),
                InventoryItem.status.ilike(pattern),
                InventoryItem.notes.ilike(pattern),
            )
        )
    if status_filter:
        query = query.filter(InventoryItem.status == status_filter)
    if department:
        query = query.filter(InventoryItem.department == department)
    if condition:
        query = query.filter(InventoryItem.condition.ilike(f"%{condition}%"))
    if location:
        query = query.filter(InventoryItem.location.ilike(f"%{location}%"))

    return query.order_by(InventoryItem.updated_at.desc()).all()


@app.post("/items", response_model=InventoryOut, status_code=status.HTTP_201_CREATED)
def create_item(payload: InventoryCreate, current_user: User = Depends(require_worker_or_admin), db: Session = Depends(get_db)):
    item = InventoryItem(**payload.model_dump(), created_by_user_id=current_user.id)
    db.add(item)
    db.flush()
    add_audit_log(db, action="Create item", user=current_user, item_id=item.id, new_value=item_snapshot(item))
    add_history(db, item=item, user=current_user)
    db.commit()
    db.refresh(item)
    return item


@app.put("/items/{item_id}", response_model=InventoryOut)
def update_item(item_id: int, payload: InventoryUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    old_snapshot = item_snapshot(item)
    old_status = item.status
    old_location = item.location
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.flush()
    new_snapshot = item_snapshot(item)
    add_audit_log(db, action="Update item", user=current_user, item_id=item.id, old_value=old_snapshot, new_value=new_snapshot)
    if old_status != item.status:
        add_audit_log(
            db,
            action="Status change",
            user=current_user,
            item_id=item.id,
            old_value={"status": old_status},
            new_value={"status": item.status},
        )
    if old_status != item.status or old_location != item.location:
        add_history(db, item=item, user=current_user)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    add_audit_log(db, action="Delete item", user=current_user, item_id=item.id, old_value=item_snapshot(item))
    db.delete(item)
    db.commit()
    return None


@app.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(AuditLog).order_by(AuditLog.created_at.desc()).all()


@app.get("/items/{item_id}/history", response_model=list[InventoryHistoryOut])
def item_history(item_id: int, _: User = Depends(require_worker_or_admin), db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return db.query(InventoryHistory).filter(InventoryHistory.item_id == item_id).order_by(InventoryHistory.created_at.desc()).all()


@app.get("/meta/statuses", response_model=list[str])
def statuses(_: User = Depends(require_worker_or_admin)):
    return [status_item.value for status_item in InventoryStatus]


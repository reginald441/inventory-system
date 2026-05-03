from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, inspect, or_, text
from sqlalchemy.orm import Session

from .auth import authenticate_user, create_access_token, hash_password, require_admin, require_auth, require_worker_or_admin
from .database import Base, engine, get_db
from .models import InventoryItem, InventoryStatus, User
from .schemas import DashboardSummary, InventoryCreate, InventoryOut, InventoryUpdate, LoginRequest, SignupRequest, TokenResponse, UserOut

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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(user), user=user)


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

    has_users = db.query(User.id).first() is not None
    role = "worker" if has_users else "admin"
    user = User(username=username, password_hash=hash_password(payload.password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=user)


@app.get("/auth/me", response_model=UserOut)
def me(current_user: User = Depends(require_auth)):
    return current_user


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
    db.commit()
    db.refresh(item)
    return item


@app.put("/items/{item_id}", response_model=InventoryOut)
def update_item(item_id: int, payload: InventoryUpdate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.delete(item)
    db.commit()
    return None


@app.get("/meta/statuses", response_model=list[str])
def statuses(_: User = Depends(require_worker_or_admin)):
    return [status_item.value for status_item in InventoryStatus]


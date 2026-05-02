from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from .auth import authenticate_user, create_access_token, require_auth
from .database import Base, engine, get_db
from .models import InventoryItem, InventoryStatus
from .schemas import DashboardSummary, InventoryCreate, InventoryOut, InventoryUpdate, LoginRequest, TokenResponse

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Warehouse Inventory Tracking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    if not authenticate_user(payload.username, payload.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    return TokenResponse(access_token=create_access_token(payload.username))


@app.get("/dashboard", response_model=DashboardSummary)
def dashboard(_: str = Depends(require_auth), db: Session = Depends(get_db)):
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
    _: str = Depends(require_auth),
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
def create_item(payload: InventoryCreate, _: str = Depends(require_auth), db: Session = Depends(get_db)):
    item = InventoryItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.put("/items/{item_id}", response_model=InventoryOut)
def update_item(item_id: int, payload: InventoryUpdate, _: str = Depends(require_auth), db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int, _: str = Depends(require_auth), db: Session = Depends(get_db)):
    item = db.get(InventoryItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    db.delete(item)
    db.commit()
    return None


@app.get("/meta/statuses", response_model=list[str])
def statuses(_: str = Depends(require_auth)):
    return [status_item.value for status_item in InventoryStatus]


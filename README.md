# Warehouse Inventory Tracking System

A full-stack inventory tracking system for Receive and IOL departments.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: FastAPI + SQLAlchemy
- Database: SQLite

## Default Login

- Username: `admin`
- Password: `admin123`

Change these values with environment variables before production use:

- `INVENTORY_ADMIN_USERNAME`
- `INVENTORY_ADMIN_PASSWORD`
- `INVENTORY_SECRET_KEY`

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will run at `http://127.0.0.1:8000`.

## Frontend Setup

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The frontend will run at `http://127.0.0.1:5173`.

## Production Build

```powershell
cd frontend
npm run build
```

## Features

- Login page with token-based authentication
- Dashboard summary counts
- Add received inventory records
- Fields: ASIN, SKU, LPN, tote ID, quantity, condition, location, department, status, notes
- Statuses: Received, IOL, Missing, Damaged, Resolved, Stowed
- Search across all fields
- Filters for status, department, condition, and location
- Inventory table view
- Edit and delete items
- CSV export
- Dark warehouse-style responsive UI


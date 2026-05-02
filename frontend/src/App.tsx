import { FormEvent, useEffect, useMemo, useState } from "react";
import { Download, LogOut, PackageCheck, Pencil, Plus, Search, Trash2, Warehouse } from "lucide-react";
import {
  clearToken,
  createItem,
  deleteItem,
  fetchDashboard,
  fetchItems,
  getToken,
  login,
  setToken,
  updateItem
} from "./api";
import type { DashboardSummary, InventoryItem, InventoryPayload, InventoryStatus } from "./types";

const statuses: InventoryStatus[] = ["Received", "IOL", "Missing", "Damaged", "Resolved", "Stowed"];
const departments = ["Receive", "IOL"] as const;

const emptyForm: InventoryPayload = {
  asin: "",
  sku: "",
  lpn: "",
  tote_id: "",
  quantity: 1,
  condition: "Sellable",
  location: "",
  department: "Receive",
  status: "Received",
  notes: ""
};

export function App() {
  const [tokenReady, setTokenReady] = useState(Boolean(getToken()));
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [authError, setAuthError] = useState("");
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [form, setForm] = useState<InventoryPayload>(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [filters, setFilters] = useState({
    q: "",
    status: "",
    department: "",
    condition: "",
    location: ""
  });

  async function loadData() {
    const [dashboardData, itemData] = await Promise.all([fetchDashboard(), fetchItems(filters)]);
    setSummary(dashboardData);
    setItems(itemData);
  }

  useEffect(() => {
    if (tokenReady) {
      loadData().catch((error) => {
        setMessage(error.message);
        if (error.message === "Invalid token") {
          clearToken();
          setTokenReady(false);
        }
      });
    }
  }, [tokenReady, filters]);

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    setAuthError("");
    try {
      const response = await login(username, password);
      setToken(response.access_token);
      setTokenReady(true);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Login failed");
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      if (editingId) {
        await updateItem(editingId, form);
        setMessage("Inventory item updated.");
      } else {
        await createItem(form);
        setMessage("Inventory item added.");
      }
      setForm(emptyForm);
      setEditingId(null);
      await loadData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Save failed");
    }
  }

  function startEdit(item: InventoryItem) {
    setEditingId(item.id);
    setForm({
      asin: item.asin,
      sku: item.sku,
      lpn: item.lpn,
      tote_id: item.tote_id,
      quantity: item.quantity,
      condition: item.condition,
      location: item.location,
      department: item.department,
      status: item.status,
      notes: item.notes
    });
  }

  async function removeItem(id: number) {
    if (!window.confirm("Delete this inventory item?")) return;
    await deleteItem(id);
    await loadData();
  }

  function exportCsv() {
    const headers = ["ID", "ASIN", "SKU", "LPN", "Tote ID", "Quantity", "Condition", "Location", "Department", "Status", "Notes", "Created", "Updated"];
    const rows = items.map((item) => [
      item.id,
      item.asin,
      item.sku,
      item.lpn,
      item.tote_id,
      item.quantity,
      item.condition,
      item.location,
      item.department,
      item.status,
      item.notes,
      item.created_at,
      item.updated_at
    ]);
    const csv = [headers, ...rows]
      .map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(","))
      .join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `warehouse-inventory-${new Date().toISOString().slice(0, 10)}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  }

  const statusCards = useMemo(() => statuses.map((status) => ({ status, count: summary?.by_status[status] ?? 0 })), [summary]);

  if (!tokenReady) {
    return (
      <main className="login-shell">
        <section className="login-panel">
          <div className="brand-mark">
            <Warehouse size={34} />
          </div>
          <h1>Warehouse Inventory</h1>
          <p>Receive and IOL tracking console</p>
          <form onSubmit={handleLogin} className="login-form">
            <label>
              Username
              <input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" />
            </label>
            <label>
              Password
              <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" />
            </label>
            {authError && <div className="error">{authError}</div>}
            <button className="primary-button" type="submit">Sign in</button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <div className="eyebrow">Receive / IOL</div>
          <h1>Inventory Tracking System</h1>
        </div>
        <button
          className="icon-button"
          title="Sign out"
          onClick={() => {
            clearToken();
            setTokenReady(false);
          }}
        >
          <LogOut size={18} />
        </button>
      </header>

      <section className="metrics">
        <div className="metric-card">
          <span>Total Records</span>
          <strong>{summary?.total_items ?? 0}</strong>
        </div>
        <div className="metric-card">
          <span>Total Units</span>
          <strong>{summary?.total_units ?? 0}</strong>
        </div>
        {statusCards.map((card) => (
          <div className="metric-card status-card" key={card.status}>
            <span>{card.status}</span>
            <strong>{card.count}</strong>
          </div>
        ))}
      </section>

      <section className="workspace">
        <form className="item-form" onSubmit={handleSubmit}>
          <div className="section-title">
            <PackageCheck size={20} />
            <h2>{editingId ? "Edit Inventory" : "Add Received Item"}</h2>
          </div>
          <div className="form-grid">
            <Field label="ASIN" value={form.asin} onChange={(value) => setForm({ ...form, asin: value })} />
            <Field label="SKU" value={form.sku} onChange={(value) => setForm({ ...form, sku: value })} />
            <Field label="LPN" value={form.lpn} onChange={(value) => setForm({ ...form, lpn: value })} />
            <Field label="Tote ID" value={form.tote_id} onChange={(value) => setForm({ ...form, tote_id: value })} />
            <label>
              Quantity
              <input type="number" min="0" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: Number(event.target.value) })} required />
            </label>
            <Field label="Condition" value={form.condition} onChange={(value) => setForm({ ...form, condition: value })} />
            <Field label="Location" value={form.location} onChange={(value) => setForm({ ...form, location: value })} />
            <label>
              Department
              <select value={form.department} onChange={(event) => setForm({ ...form, department: event.target.value as InventoryPayload["department"] })}>
                {departments.map((department) => <option key={department}>{department}</option>)}
              </select>
            </label>
            <label>
              Status
              <select value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as InventoryStatus })}>
                {statuses.map((status) => <option key={status}>{status}</option>)}
              </select>
            </label>
            <label className="wide">
              Notes
              <textarea value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} rows={3} />
            </label>
          </div>
          {message && <div className="message">{message}</div>}
          <div className="form-actions">
            <button className="primary-button" type="submit">
              <Plus size={16} />
              {editingId ? "Save Changes" : "Add Item"}
            </button>
            {editingId && (
              <button
                className="secondary-button"
                type="button"
                onClick={() => {
                  setEditingId(null);
                  setForm(emptyForm);
                }}
              >
                Cancel
              </button>
            )}
          </div>
        </form>

        <section className="table-section">
          <div className="table-tools">
            <div className="search-box">
              <Search size={18} />
              <input placeholder="Search all fields" value={filters.q} onChange={(event) => setFilters({ ...filters, q: event.target.value })} />
            </div>
            <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
              <option value="">All statuses</option>
              {statuses.map((status) => <option key={status}>{status}</option>)}
            </select>
            <select value={filters.department} onChange={(event) => setFilters({ ...filters, department: event.target.value })}>
              <option value="">All departments</option>
              {departments.map((department) => <option key={department}>{department}</option>)}
            </select>
            <input placeholder="Condition" value={filters.condition} onChange={(event) => setFilters({ ...filters, condition: event.target.value })} />
            <input placeholder="Location" value={filters.location} onChange={(event) => setFilters({ ...filters, location: event.target.value })} />
            <button className="secondary-button" type="button" onClick={exportCsv}>
              <Download size={16} />
              CSV
            </button>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ASIN</th>
                  <th>SKU</th>
                  <th>LPN</th>
                  <th>Tote</th>
                  <th>Qty</th>
                  <th>Condition</th>
                  <th>Location</th>
                  <th>Dept</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.asin}</td>
                    <td>{item.sku}</td>
                    <td>{item.lpn}</td>
                    <td>{item.tote_id}</td>
                    <td>{item.quantity}</td>
                    <td>{item.condition}</td>
                    <td>{item.location}</td>
                    <td>{item.department}</td>
                    <td><span className={`pill ${item.status.toLowerCase()}`}>{item.status}</span></td>
                    <td>{new Date(item.updated_at).toLocaleString()}</td>
                    <td className="row-actions">
                      <button title="Edit" className="icon-button" onClick={() => startEdit(item)}><Pencil size={16} /></button>
                      <button title="Delete" className="icon-button danger" onClick={() => removeItem(item.id)}><Trash2 size={16} /></button>
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={11} className="empty">No inventory records match the current filters.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </section>
    </main>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label>
      {label}
      <input value={value} onChange={(event) => onChange(event.target.value)} required />
    </label>
  );
}


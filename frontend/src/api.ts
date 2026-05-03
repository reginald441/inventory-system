import type { AuditLog, DashboardSummary, InventoryHistory, InventoryItem, InventoryPayload, User } from "./types";

const API_BASE = "https://inventory-system-production-dfa0.up.railway.app";
const TOKEN_KEY = "warehouse_inventory_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(detail.detail || "Request failed");
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json();
}

export async function login(username: string, password: string) {
  return request<{ access_token: string; token_type: string; user: User }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export async function signup(username: string, password: string) {
  return request<{ access_token: string; token_type: string; user: User }>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export async function fetchCurrentUser() {
  return request<User>("/auth/me");
}

export async function fetchDashboard() {
  return request<DashboardSummary>("/dashboard");
}

export async function fetchItems(filters: Record<string, string>) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value.trim()) params.set(key, value.trim());
  });
  const query = params.toString();
  return request<InventoryItem[]>(`/items${query ? `?${query}` : ""}`);
}

export async function createItem(payload: InventoryPayload) {
  return request<InventoryItem>("/items", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function updateItem(id: number, payload: InventoryPayload) {
  return request<InventoryItem>(`/items/${id}`, {
    method: "PUT",
    body: JSON.stringify(payload)
  });
}

export async function deleteItem(id: number) {
  return request<void>(`/items/${id}`, { method: "DELETE" });
}

export async function fetchAuditLogs() {
  return request<AuditLog[]>("/audit-logs");
}

export async function fetchItemHistory(id: number) {
  return request<InventoryHistory[]>(`/items/${id}/history`);
}


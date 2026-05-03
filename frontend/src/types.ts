export type InventoryStatus = "Received" | "IOL" | "Missing" | "Damaged" | "Resolved" | "Stowed";
export type Department = "Receive" | "IOL";
export type UserRole = "admin" | "worker";

export type User = {
  id: number;
  username: string;
  role: UserRole;
  created_at: string;
};

export type InventoryItem = {
  id: number;
  asin: string;
  sku: string;
  lpn: string;
  tote_id: string;
  quantity: number;
  condition: string;
  location: string;
  department: Department;
  status: InventoryStatus;
  notes: string;
  created_by_user_id: number | null;
  created_by_username: string | null;
  created_at: string;
  updated_at: string;
};

export type InventoryPayload = Omit<InventoryItem, "id" | "created_by_user_id" | "created_by_username" | "created_at" | "updated_at">;

export type DashboardSummary = {
  total_items: number;
  total_units: number;
  by_status: Record<string, number>;
  by_department: Record<string, number>;
};

export type AuditLog = {
  id: number;
  action: string;
  item_id: number | null;
  user_id: number | null;
  username: string;
  old_value: string | null;
  new_value: string | null;
  created_at: string;
};

export type InventoryHistory = {
  id: number;
  item_id: number;
  status: string;
  location: string;
  notes: string;
  changed_by_user_id: number | null;
  created_at: string;
};


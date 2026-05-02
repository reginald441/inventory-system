export type InventoryStatus = "Received" | "IOL" | "Missing" | "Damaged" | "Resolved" | "Stowed";
export type Department = "Receive" | "IOL";

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
  created_at: string;
  updated_at: string;
};

export type InventoryPayload = Omit<InventoryItem, "id" | "created_at" | "updated_at">;

export type DashboardSummary = {
  total_items: number;
  total_units: number;
  by_status: Record<string, number>;
  by_department: Record<string, number>;
};


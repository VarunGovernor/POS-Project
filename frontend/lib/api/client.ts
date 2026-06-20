export type ApiSuccess<T> = {
  success: true;
  data: T;
  request_id: string;
};

export type ApiFailure = {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
  };
  request_id: string;
};

export type ApiResponse<T> = ApiSuccess<T> | ApiFailure;

export type HealthData = {
  status: string;
  api: string;
  database: string;
  sync: string;
  printer: string;
  recovery: string;
  storage: string;
  license: string;
  device: string;
  tenant: string;
  migration: string;
  unsynced_event_count: number;
  failed_event_count: number;
  last_sync_at: string | null;
  last_backup_at: string | null;
};

export type VersionData = {
  api_version: string;
  app_version: string;
  backend_version: string;
  frontend_version: string;
  database_version: string;
  environment: string;
};

export type StartupStatusData = {
  startup_status: string;
  api_status: string;
  database_status: string;
  recovery_required: boolean;
  migration_status: string;
  device_status: string;
  license_status: string;
  tenant_status: string;
  printer_status: string;
  sync_status: string;
  app_version: string;
  backend_version: string;
  frontend_version: string;
  database_version: string;
};

export type AuthUser = {
  id: string;
  username: string;
  display_name: string;
  roles: string[];
  permissions: string[];
};

export type LoginData = {
  session_token: string;
  user: AuthUser;
  offline_login: boolean;
  expires_at: string;
};

export type MeData = {
  user: AuthUser;
  login_session_id: string;
  expires_at: string;
};

export type DeviceStatusData = {
  device_id: string;
  device_code: string;
  device_name: string;
  installation_id: string;
  organization_id: string;
  branch_id: string;
  counter_name: string;
  status: string;
  activation_status: string;
  last_successful_sync_at: string | null;
  last_master_sync_at: string | null;
};

export type CashierSession = {
  id: string;
  session_number: string;
  status: string;
  counter_name: string;
  opening_cash_amount: number;
  closing_cash_amount: number | null;
  expected_cash_amount: number | null;
  cash_difference_amount: number | null;
  opened_at: string;
  closed_at: string | null;
  notes: string | null;
};

export type Patient = {
  id: string;
  patient_number: string;
  full_name: string;
  phone: string | null;
  gender: string | null;
  age_years: number | null;
  sync_status: string;
};

export type ServiceItem = {
  id: string;
  service_code: string;
  service_name: string;
  service_type: string;
  department_id: string | null;
  department_name: string | null;
  default_price: number | null;
  currency: string | null;
  catalog_version: string;
  price_version: string | null;
  status: string;
};

export type Department = {
  id: string;
  department_code: string;
  department_name: string;
  status: string;
};

export type Doctor = {
  id: string;
  doctor_code: string;
  full_name: string;
  specialization: string | null;
  department_id: string | null;
  department_name: string | null;
  status: string;
};

export type MasterSyncState = {
  id: string;
  master_type: string;
  version_code: string;
  last_successful_sync_at: string | null;
  status: string;
};

export type DraftItem = {
  id: string;
  service_id: string;
  service_name_at_time: string;
  department_id_at_time: string | null;
  department_name_at_time: string | null;
  quantity: number;
  unit_price_at_time: number;
  gross_amount: number;
  discount_amount: number;
  tax_amount: number;
  final_line_total: number;
  catalog_version: string;
  price_version: string;
};

export type BillDraft = {
  id: string;
  draft_number: string;
  status: string;
  patient_id?: string | null;
  patient_name?: string | null;
  bill_type: string;
  department_id?: string | null;
  doctor_id?: string | null;
  subtotal_amount?: number;
  discount_amount?: number;
  tax_amount?: number;
  total_amount: number;
  last_autosaved_at?: string;
  updated_at?: string;
  patient?: { id: string; full_name: string; phone: string | null } | null;
  items?: DraftItem[];
};

export type FinalBill = {
  id: string;
  bill_number: string;
  status: string;
  currency: string;
  subtotal_amount: number;
  discount_amount: number;
  tax_amount: number;
  total_amount: number;
  sync_status: string;
  finalized_at: string;
  patient_name?: string | null;
  patient?: { id: string; full_name: string; phone: string | null; patient_number?: string } | null;
  items?: Array<{ id: string; service_name_at_time: string; quantity: number; unit_price: number; final_line_total: number; catalog_version: string; price_version: string }>;
  payment?: { id: string; payment_number: string; payment_method: string; status: string; amount: number; received_amount: number; change_amount: number; paid_at: string } | null;
  receipt?: { id: string; receipt_number: string; status: string; receipt_type: string; generated_at: string } | null;
};

export type Receipt = {
  id: string;
  receipt_number: string;
  status: string;
  receipt_type: string;
  generated_at: string;
  receipt_payload: Record<string, unknown> & { items?: Array<Record<string, unknown>> };
};

export type PrinterJob = {
  id: string;
  job_number: string;
  job_type: string;
  status: string;
  attempt_count: number;
  printed_at: string | null;
  failure_message: string | null;
};

export type PrinterStatus = {
  status: string;
  printer: {
    id: string;
    printer_code: string;
    printer_name: string;
    printer_type: string;
    connection_type: string;
    is_default: boolean;
    last_seen_at: string | null;
  } | null;
  queued_job_count: number;
  failed_job_count: number;
  last_printed_at: string | null;
};

export type RecoveryStatus = {
  recovery_required: boolean;
  open_marker_count: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  last_scan_at: string | null;
};

export type RecoveryMarker = {
  id: string;
  marker_code: string;
  marker_type: string;
  severity: string;
  status: string;
  entity_type: string | null;
  entity_id: string | null;
  title: string;
  description: string;
  detected_at: string;
};

export type SyncStatus = {
  status: string;
  pending_count: number;
  syncing_count: number;
  synced_count: number;
  failed_retryable_count: number;
  failed_permanent_count: number;
  conflict_count: number;
  last_successful_sync_at: string | null;
  last_attempt_at: string | null;
  adapter: string;
};

export type SyncEvent = {
  id: string;
  event_type: string;
  entity_type: string;
  entity_id: string;
  status: string;
  attempt_count: number;
  last_attempt_at: string | null;
  next_attempt_at: string | null;
  created_at: string;
};

export type SyncConflict = {
  id: string;
  sync_event_id: string;
  entity_type: string;
  entity_id: string;
  conflict_type: string;
  resolution_status: string;
  created_at: string;
};

const API_BASE_URL = process.env.NEXT_PUBLIC_LOCAL_API_URL ?? "http://127.0.0.1:8000";

type RequestOptions = {
  method?: string;
  token?: string | null;
  body?: Record<string, unknown>;
  headers?: Record<string, string>;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<ApiSuccess<T>> {
  const headers: Record<string, string> = {
    Accept: "application/json"
  };
  if (options.body) {
    headers["Content-Type"] = "application/json";
  }
  if (options.token) {
    headers.Authorization = `Bearer ${options.token}`;
  }
  Object.assign(headers, options.headers);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: options.method ?? "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
    cache: "no-store"
  });

  const body = (await response.json()) as ApiResponse<T>;
  if (!body.success) {
    throw new Error(`${body.error.code}: ${body.error.message}`);
  }

  return body;
}

export const localApi = {
  health: () => request<HealthData>("/api/v1/health"),
  version: () => request<VersionData>("/api/v1/health/version"),
  startupStatus: () => request<StartupStatusData>("/api/v1/startup/status"),
  login: (body: { username: string; password: string; counter_name: string }) =>
    request<LoginData>("/api/v1/auth/login", { method: "POST", body }),
  me: (token: string | null) => request<MeData>("/api/v1/auth/me", { token }),
  logout: (token: string | null) => request<{ status: string }>("/api/v1/auth/logout", { method: "POST", token }),
  deviceStatus: (token: string | null) => request<DeviceStatusData>("/api/v1/device/status", { token }),
  currentSession: (token: string | null) =>
    request<{ session: CashierSession | null }>("/api/v1/sessions/current", { token }),
  openSession: (token: string | null, body: { counter_name: string; opening_cash_amount: number; notes?: string }) =>
    request<{ session: CashierSession }>("/api/v1/sessions/open", { method: "POST", token, body }),
  closeSession: (token: string | null, body: { session_id: string; closing_cash_amount: number; notes?: string }) =>
    request<{ session: CashierSession }>("/api/v1/sessions/close", { method: "POST", token, body }),
  patients: (token: string | null, q = "") =>
    request<{ items: Patient[]; page: number; page_size: number; total: number; has_next: boolean }>(
      `/api/v1/patients${q ? `?q=${encodeURIComponent(q)}` : ""}`,
      { token }
    ),
  createPatient: (
    token: string | null,
    body: { full_name: string; phone?: string; gender?: string; age_years?: number; address_line1?: string }
  ) => request<{ patient: Patient }>("/api/v1/patients", { method: "POST", token, body }),
  services: (token: string | null, q = "") =>
    request<{ items: ServiceItem[]; page: number; page_size: number; total: number; has_next: boolean }>(
      `/api/v1/catalog/services${q ? `?q=${encodeURIComponent(q)}` : ""}`,
      { token }
    ),
  departments: (token: string | null) => request<{ items: Department[] }>("/api/v1/catalog/departments", { token }),
  doctors: (token: string | null) => request<{ items: Doctor[] }>("/api/v1/catalog/doctors", { token }),
  masterSyncState: (token: string | null) =>
    request<{ items: MasterSyncState[] }>("/api/v1/catalog/master-sync-state", { token }),
  createDraft: (token: string | null, body: { patient_id?: string; bill_type: string; department_id?: string; doctor_id?: string; notes?: string }) =>
    request<{ draft: BillDraft }>("/api/v1/bills/drafts", { method: "POST", token, body }),
  drafts: (token: string | null) =>
    request<{ items: BillDraft[]; page: number; page_size: number; total: number; has_next: boolean }>("/api/v1/bills/drafts", { token }),
  draft: (token: string | null, draftId: string) => request<{ draft: BillDraft }>(`/api/v1/bills/drafts/${draftId}`, { token }),
  addDraftItem: (token: string | null, draftId: string, body: { service_id: string; quantity: number; discount_amount?: number; doctor_id?: string; notes?: string }) =>
    request<{ item: DraftItem; totals: { subtotal_amount: number; discount_amount: number; tax_amount: number; total_amount: number }; last_autosaved_at: string }>(
      `/api/v1/bills/drafts/${draftId}/items`,
      { method: "POST", token, body }
    ),
  updateDraftItem: (token: string | null, draftId: string, itemId: string, body: { quantity: number; discount_amount?: number; notes?: string }) =>
    request<{ item: DraftItem; totals: { subtotal_amount: number; discount_amount: number; tax_amount: number; total_amount: number }; last_autosaved_at: string }>(
      `/api/v1/bills/drafts/${draftId}/items/${itemId}`,
      { method: "PATCH", token, body }
    ),
  removeDraftItem: (token: string | null, draftId: string, itemId: string) =>
    request<{ removed: boolean; totals: { subtotal_amount: number; discount_amount: number; tax_amount: number; total_amount: number }; last_autosaved_at: string }>(
      `/api/v1/bills/drafts/${draftId}/items/${itemId}`,
      { method: "DELETE", token }
    ),
  voidDraft: (token: string | null, draftId: string, reason: string) =>
    request<{ draft: BillDraft }>(`/api/v1/bills/drafts/${draftId}/void`, { method: "POST", token, body: { reason } }),
  finalizeDraft: (token: string | null, draftId: string, idempotencyKey: string, body: { payment_method: "cash"; received_amount: number; notes?: string }) =>
    request<{
      bill: FinalBill;
      payment: NonNullable<FinalBill["payment"]>;
      receipt: NonNullable<FinalBill["receipt"]>;
      sync_event: { id: string; event_type: string; status: string };
    }>(`/api/v1/bills/drafts/${draftId}/finalize`, {
      method: "POST",
      token,
      body,
      headers: { "Idempotency-Key": idempotencyKey }
    }),
  bills: (token: string | null) =>
    request<{ items: FinalBill[]; page: number; page_size: number; total: number; has_next: boolean }>("/api/v1/bills", { token }),
  bill: (token: string | null, billId: string) => request<{ bill: FinalBill }>(`/api/v1/bills/${billId}`, { token }),
  receiptByBill: (token: string | null, billId: string) => request<{ receipt: Receipt }>(`/api/v1/receipts/by-bill/${billId}`, { token }),
  printerStatus: (token: string | null) => request<PrinterStatus>("/api/v1/printer/status", { token }),
  printerJobs: (token: string | null) =>
    request<{ items: PrinterJob[]; page: number; page_size: number; total: number; has_next: boolean }>("/api/v1/printer/jobs", { token }),
  printerTest: (token: string | null) => request<{ job: PrinterJob }>("/api/v1/printer/test", { method: "POST", token }),
  retryPrinterJob: (token: string | null, jobId: string) => request<{ job: PrinterJob }>(`/api/v1/printer/jobs/${jobId}/retry`, { method: "POST", token }),
  printReceipt: (token: string | null, receiptId: string) => request<{ job: PrinterJob }>(`/api/v1/receipts/${receiptId}/print`, { method: "POST", token }),
  reprintReceipt: (token: string | null, receiptId: string, reason: string) =>
    request<{ job: PrinterJob }>(`/api/v1/receipts/${receiptId}/reprint`, { method: "POST", token, body: { reason } }),
  recoveryStatus: (token: string | null) => request<RecoveryStatus>("/api/v1/recovery/status", { token }),
  recoveryItems: (token: string | null) =>
    request<{ items: RecoveryMarker[]; page: number; page_size: number; total: number; has_next: boolean }>("/api/v1/recovery/work-items", { token }),
  recoveryScan: (token: string | null) => request<RecoveryStatus>("/api/v1/recovery/scan", { method: "POST", token }),
  recoveryResolve: (token: string | null, markerId: string, resolution_action = "acknowledged") =>
    request<{ marker: RecoveryMarker }>("/api/v1/recovery/resolve", { method: "POST", token, body: { marker_id: markerId, resolution_action } }),
  syncStatus: (token: string | null) => request<SyncStatus>("/api/v1/sync/status", { token }),
  syncEvents: (token: string | null) =>
    request<{ items: SyncEvent[]; page: number; page_size: number; total: number; has_next: boolean }>("/api/v1/sync/events", { token }),
  syncRetryAll: (token: string | null) => request<{ attempted: number; synced: number; failed: number; conflicts: number }>("/api/v1/sync/retry", { method: "POST", token }),
  syncRetryEvent: (token: string | null, eventId: string) => request<{ event: SyncEvent }>(`/api/v1/sync/events/${eventId}/retry`, { method: "POST", token }),
  syncConflicts: (token: string | null) => request<{ items: SyncConflict[] }>("/api/v1/sync/conflicts", { token })
};

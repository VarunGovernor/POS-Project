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

const API_BASE_URL = process.env.NEXT_PUBLIC_LOCAL_API_URL ?? "http://127.0.0.1:8000";

type RequestOptions = {
  method?: string;
  token?: string | null;
  body?: Record<string, unknown>;
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
    request<{ session: CashierSession }>("/api/v1/sessions/close", { method: "POST", token, body })
};

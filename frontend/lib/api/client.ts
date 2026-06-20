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

const API_BASE_URL = process.env.NEXT_PUBLIC_LOCAL_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string): Promise<ApiSuccess<T>> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json"
    },
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
  startupStatus: () => request<StartupStatusData>("/api/v1/startup/status")
};

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { RecoveryScreen } from "@/app/recovery/RecoveryScreen";
import { StartupScreen } from "@/app/startup/StartupScreen";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() })
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  )
}));

function ok(data: unknown) {
  return Promise.resolve(new Response(JSON.stringify({ success: true, data, request_id: "REQ-TEST" })));
}

function fail(code: string, message: string) {
  return Promise.resolve(new Response(JSON.stringify({ success: false, error: { code, message, details: {} }, request_id: "REQ-TEST" })));
}

const status = {
  recovery_required: true,
  open_marker_count: 1,
  critical_count: 0,
  warning_count: 1,
  info_count: 0,
  last_scan_at: "now"
};
const marker = {
  id: "1",
  marker_code: "REC-1",
  marker_type: "ACTIVE_SESSION_FOUND",
  severity: "warning",
  status: "open",
  entity_type: "cashier_session",
  entity_id: "1",
  title: "Active cashier session found",
  description: "A cashier session is still open after startup.",
  detected_at: "now"
};

describe("Phase 7 recovery UI", () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: {
        clear: () => store.clear(),
        getItem: (key: string) => store.get(key) ?? null,
        removeItem: (key: string) => store.delete(key),
        setItem: (key: string, value: string) => store.set(key, value)
      }
    });
    vi.restoreAllMocks();
    localStorage.setItem("counteros_token", "TOKEN");
  });

  test("recovery status loads and work items render", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => String(input).includes("/status") ? ok(status) : ok({ items: [marker], page: 1, page_size: 25, total: 1, has_next: false }));
    render(<RecoveryScreen />);
    await waitFor(() => expect(screen.getByText("Active cashier session found")).toBeInTheDocument());
    expect(screen.getByText("required")).toBeInTheDocument();
  });

  test("empty state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => String(input).includes("/status") ? ok({ ...status, recovery_required: false, open_marker_count: 0, warning_count: 0 }) : ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false }));
    render(<RecoveryScreen />);
    await waitFor(() => expect(screen.getByText("No recovery work items.")).toBeInTheDocument());
  });

  test("scan and resolve call APIs", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/scan")) return ok(status);
      if (url.includes("/resolve")) return ok({ marker: { ...marker, status: "acknowledged" } });
      if (url.includes("/status")) return ok(status);
      return ok({ items: [marker], page: 1, page_size: 25, total: 1, has_next: false });
    });
    render(<RecoveryScreen />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Scan" })).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Scan" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/recovery/scan", expect.objectContaining({ method: "POST" })));
    await userEvent.click(screen.getByRole("button", { name: "Acknowledge" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/recovery/resolve", expect.objectContaining({ method: "POST" })));
  });

  test("permission denied state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() => fail("AUTH_PERMISSION_DENIED", "Permission denied."));
    render(<RecoveryScreen />);
    await waitFor(() => expect(screen.getByText("Permission denied.")).toBeInTheDocument());
  });

  test("startup recovery required indicator renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/startup/status")) return ok({ startup_status: "ready", api_status: "ok", database_status: "ok", recovery_required: true, migration_status: "ok", device_status: "active", license_status: "not_configured", tenant_status: "not_configured", printer_status: "active", sync_status: "not_configured", app_version: "0.1.0", backend_version: "0.1.0", frontend_version: "0.1.0", database_version: "PHASE_7_RECOVERY_FOUNDATION" });
      if (url.endsWith("/api/v1/health/version")) return ok({ api_version: "v1", app_version: "0.1.0", backend_version: "0.1.0", frontend_version: "0.1.0", database_version: "PHASE_7_RECOVERY_FOUNDATION", environment: "development" });
      return ok({ status: "ok", api: "ok", database: "ok", sync: "not_configured", printer: "active", recovery: "required", storage: "not_configured", license: "not_configured", device: "active", tenant: "not_configured", migration: "ok", unsynced_event_count: 0, failed_event_count: 0, last_sync_at: null, last_backup_at: null });
    });
    render(<StartupScreen />);
    await waitFor(() => expect(screen.getByText("Recovery required")).toBeInTheDocument());
    expect(screen.getByText("yes")).toBeInTheDocument();
  });
});

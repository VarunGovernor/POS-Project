import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { AuditScreen } from "@/app/audit/AuditScreen";
import { ReportsScreen } from "@/app/reports/ReportsScreen";
import { SettingsScreen } from "@/app/settings/SettingsScreen";
import { SupportScreen } from "@/app/support/SupportScreen";

function ok(data: unknown) {
  return Promise.resolve(new Response(JSON.stringify({ success: true, data, request_id: "REQ-TEST" })));
}

function fail(code: string, message: string) {
  return Promise.resolve(new Response(JSON.stringify({ success: false, error: { code, message, details: {} }, request_id: "REQ-TEST" })));
}

const me = { user: { id: "2", username: "admin", display_name: "Admin", roles: ["admin"], permissions: ["report.department.view"] }, login_session_id: "1", expires_at: "later" };

describe("Phase 9 operations UI", () => {
  beforeEach(() => {
    const store = new Map<string, string>();
    Object.defineProperty(globalThis, "localStorage", {
      configurable: true,
      value: {
        getItem: (key: string) => store.get(key) ?? null,
        setItem: (key: string, value: string) => store.set(key, value),
        removeItem: (key: string) => store.delete(key),
        clear: () => store.clear()
      }
    });
    vi.restoreAllMocks();
    localStorage.setItem("counteros_token", "TOKEN");
  });

  test("reports screen renders real API data", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/auth/me")) return ok(me);
      if (url.includes("/today-collection")) return ok({ business_date: "2026-06-20", currency: "INR", bill_count: 1, gross_amount: 500, discount_amount: 0, tax_amount: 0, net_amount: 500, cash_collected: 500, receipt_count: 1, printed_receipt_count: 0, pending_sync_count: 1 });
      if (url.includes("/department-collection")) return ok({ items: [{ department_name: "General Medicine", bill_count: 1, net_amount: 500 }] });
      return ok({ by_status: [{ status: "pending", count: 1 }], by_event_type: [] });
    });
    render(<ReportsScreen />);
    await waitFor(() => expect(screen.getAllByText("500 INR").length).toBeGreaterThan(0));
    expect(screen.getByText("General Medicine: 500")).toBeInTheDocument();
  });

  test("settings screen renders and update calls API", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.includes("/settings") && init?.method === "PATCH") return ok({ setting: { id: "2", setting_key: "receipt.header", setting_value: "Updated", setting_scope: "device", is_readonly: false } });
      return ok({ items: [{ id: "2", setting_key: "receipt.header", setting_value: "CounterOS Hospital", setting_scope: "device", is_readonly: false }, { id: "1", setting_key: "environment", setting_value: "development", setting_scope: "device", is_readonly: true }] });
    });
    render(<SettingsScreen />);
    await waitFor(() => expect(screen.getByDisplayValue("CounterOS Hospital")).toBeInTheDocument());
    const input = screen.getByDisplayValue("CounterOS Hospital");
    await userEvent.clear(input);
    await userEvent.type(input, "Updated");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/settings", expect.objectContaining({ method: "PATCH" })));
    expect(screen.getByText("readonly")).toBeInTheDocument();
  });

  test("support status and bundle action call APIs", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/bundle")) return ok({ bundle: { bundle_id: "SUP-1", status: "created", file_path: "/tmp/SUP-1.json", created_at: "now" } });
      return ok({ api: "ok", database: "ok", printer: "active", sync: "pending", recovery: "ok", storage: "ok", app_version: "0.1.0", backend_version: "0.1.0", database_version: "PHASE_9_REPORTS_SUPPORT", pending_sync_count: 1, failed_sync_count: 0, failed_print_job_count: 0, open_recovery_marker_count: 0 });
    });
    render(<SupportScreen />);
    await waitFor(() => expect(screen.getByText("PHASE_9_REPORTS_SUPPORT")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Create Bundle" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/support/bundle", expect.objectContaining({ method: "POST" })));
    expect(screen.getByText("Bundle created: SUP-1")).toBeInTheDocument();
  });

  test("audit screen renders and permission denied state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() => ok({ items: [{ id: "1", action: "auth.login", entity_type: null, entity_id: null, severity: "info", request_id: "REQ", created_at: "now" }], page: 1, page_size: 25, total: 1, has_next: false }));
    render(<AuditScreen />);
    await waitFor(() => expect(screen.getByText("auth.login")).toBeInTheDocument());

    vi.restoreAllMocks();
    vi.spyOn(global, "fetch").mockImplementation(() => fail("AUTH_PERMISSION_DENIED", "Permission denied."));
    render(<AuditScreen />);
    await waitFor(() => expect(screen.getByText("Permission denied.")).toBeInTheDocument());
  });

  test("error state renders", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new Error("fetch failed"));
    render(<ReportsScreen />);
    await waitFor(() => expect(screen.getByText("API unavailable.")).toBeInTheDocument());
  });
});

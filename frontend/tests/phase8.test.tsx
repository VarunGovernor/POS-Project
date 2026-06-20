import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { SyncScreen } from "@/app/sync/SyncScreen";

function ok(data: unknown) {
  return Promise.resolve(new Response(JSON.stringify({ success: true, data, request_id: "REQ-TEST" })));
}

function fail(code: string, message: string) {
  return Promise.resolve(new Response(JSON.stringify({ success: false, error: { code, message, details: {} }, request_id: "REQ-TEST" })));
}

const me = { user: { id: "2", username: "admin", display_name: "Admin", roles: ["admin"], permissions: ["sync.run", "sync.conflict.view"] }, login_session_id: "1", expires_at: "later" };
const status = {
  status: "pending",
  pending_count: 1,
  syncing_count: 0,
  synced_count: 0,
  failed_retryable_count: 0,
  failed_permanent_count: 0,
  conflict_count: 0,
  last_successful_sync_at: null,
  last_attempt_at: null,
  adapter: "development"
};
const event = {
  id: "1",
  event_type: "BILL_FINALIZED",
  entity_type: "bill",
  entity_id: "1",
  status: "pending",
  attempt_count: 0,
  last_attempt_at: null,
  next_attempt_at: null,
  created_at: "now"
};

describe("Phase 8 sync UI", () => {
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

  test("sync status, events, and conflicts render", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/auth/me")) return ok(me);
      if (url.includes("/sync/status")) return ok(status);
      if (url.includes("/sync/conflicts")) return ok({ items: [] });
      return ok({ items: [event], page: 1, page_size: 25, total: 1, has_next: false });
    });
    render(<SyncScreen />);
    await waitFor(() => expect(screen.getByText("BILL_FINALIZED")).toBeInTheDocument());
    expect(screen.getByText("development")).toBeInTheDocument();
    expect(screen.getByText("No sync conflicts.")).toBeInTheDocument();
  });

  test("empty state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/auth/me")) return ok(me);
      if (url.includes("/sync/status")) return ok({ ...status, status: "ok", pending_count: 0 });
      if (url.includes("/sync/conflicts")) return ok({ items: [] });
      return ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false });
    });
    render(<SyncScreen />);
    await waitFor(() => expect(screen.getByText("No sync events.")).toBeInTheDocument());
  });

  test("retry all and retry single call APIs", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/auth/me")) return ok(me);
      if (url.endsWith("/sync/retry")) return ok({ attempted: 1, synced: 1, failed: 0, conflicts: 0 });
      if (url.includes("/events/1/retry")) return ok({ event: { ...event, status: "synced" } });
      if (url.includes("/sync/status")) return ok(status);
      if (url.includes("/sync/conflicts")) return ok({ items: [] });
      return ok({ items: [event], page: 1, page_size: 25, total: 1, has_next: false });
    });
    render(<SyncScreen />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Retry All" })).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Retry All" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/sync/retry", expect.objectContaining({ method: "POST" })));
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/sync/events/1/retry", expect.objectContaining({ method: "POST" })));
  });

  test("permission denied state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() => fail("AUTH_PERMISSION_DENIED", "Permission denied."));
    render(<SyncScreen />);
    await waitFor(() => expect(screen.getByText("Permission denied.")).toBeInTheDocument());
  });
});

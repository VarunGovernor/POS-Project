import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { DashboardScreen } from "@/app/dashboard/DashboardScreen";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push })
}));

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>{children}</a>
  )
}));

function ok(data: unknown) {
  return Promise.resolve(new Response(JSON.stringify({ success: true, data, request_id: "REQ-TEST" })));
}

describe("Phase 11 hardening UI", () => {
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

  test("dashboard links route only to implemented screens", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) return ok({ user: { id: "1", username: "cashier", display_name: "Cashier", roles: ["cashier"], permissions: [] }, login_session_id: "1", expires_at: "later" });
      if (url.endsWith("/api/v1/device/status")) return ok({ device_id: "1", device_code: "DEV", device_name: "Device", installation_id: "INSTALL", organization_id: "1", branch_id: "1", counter_name: "OP", status: "active", activation_status: "active", last_successful_sync_at: null, last_master_sync_at: null });
      return ok({ session: null });
    });

    render(<DashboardScreen />);
    await waitFor(() => expect(screen.getByText("Cashier")).toBeInTheDocument());

    const expected = [
      "/session/open",
      "/registrations",
      "/patients",
      "/billing/new",
      "/billing/drafts",
      "/billing/bills",
      "/printer",
      "/sync",
      "/recovery",
      "/reports",
      "/settings",
      "/support",
      "/audit"
    ];
    const links = screen.getAllByRole("link").map((link) => link.getAttribute("href"));
    expect(links).toEqual(expected);
    expect(links).not.toContain("#");
    expect(screen.queryByText(/refund|gateway|coming soon|placeholder/i)).not.toBeInTheDocument();
  });
});

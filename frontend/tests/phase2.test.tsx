import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { DashboardScreen } from "@/app/dashboard/DashboardScreen";
import { LoginScreen } from "@/app/login/LoginScreen";
import { CloseSessionScreen } from "@/app/session/close/CloseSessionScreen";
import { OpenSessionScreen } from "@/app/session/open/OpenSessionScreen";

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
  return Promise.resolve(
    new Response(JSON.stringify({ success: true, data, request_id: "REQ-TEST" }))
  );
}

function fail(code: string, message: string) {
  return Promise.resolve(
    new Response(JSON.stringify({ success: false, error: { code, message, details: {} }, request_id: "REQ-TEST" }))
  );
}

const user = {
  id: "1",
  username: "cashier",
  display_name: "Cashier",
  roles: ["cashier"],
  permissions: ["session.view", "session.open", "session.close", "device.view"]
};

const device = {
  device_id: "1",
  device_code: "DEV_DEVICE",
  device_name: "Development Device",
  installation_id: "DEV-INSTALLATION",
  organization_id: "1",
  branch_id: "1",
  counter_name: "OP Counter 1",
  status: "active",
  activation_status: "active",
  last_successful_sync_at: null,
  last_master_sync_at: null
};

const session = {
  id: "1",
  session_number: "CS-1",
  status: "open",
  counter_name: "OP Counter 1",
  opening_cash_amount: 1000,
  closing_cash_amount: null,
  expected_cash_amount: null,
  cash_difference_amount: null,
  opened_at: "2026-01-01T00:00:00Z",
  closed_at: null,
  notes: "Morning shift"
};

describe("Phase 2 screens", () => {
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
    push.mockReset();
    localStorage.clear();
  });

  test("login screen renders", () => {
    render(<LoginScreen />);
    expect(screen.getByRole("heading", { name: "Login" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Login" })).toBeInTheDocument();
  });

  test("login calls API successfully", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation(() =>
      ok({ session_token: "TOKEN", user, offline_login: false, expires_at: "2026-01-01T12:00:00Z" })
    );

    render(<LoginScreen />);
    await userEvent.type(screen.getByLabelText("Password"), "cashier123");
    await userEvent.click(screen.getByRole("button", { name: "Login" }));

    await waitFor(() => expect(push).toHaveBeenCalledWith("/dashboard"));
    expect(localStorage.getItem("counteros_token")).toBe("TOKEN");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/auth/login",
      expect.objectContaining({ method: "POST" })
    );
  });

  test("dashboard renders current user device and session", async () => {
    localStorage.setItem("counteros_token", "TOKEN");
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) return ok({ user, login_session_id: "1", expires_at: "2026-01-01T12:00:00Z" });
      if (url.endsWith("/api/v1/device/status")) return ok(device);
      return ok({ session });
    });

    render(<DashboardScreen />);

    await waitFor(() => expect(screen.getByText("Cashier")).toBeInTheDocument());
    expect(screen.getByText("Development Device")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Close Session" })).toHaveAttribute("href", "/session/close");
  });

  test("open session screen renders", () => {
    render(<OpenSessionScreen />);
    expect(screen.getByRole("heading", { name: "Open Session" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Session" })).toBeInTheDocument();
  });

  test("close session screen renders", async () => {
    localStorage.setItem("counteros_token", "TOKEN");
    vi.spyOn(global, "fetch").mockImplementation(() => ok({ session }));

    render(<CloseSessionScreen />);

    await waitFor(() => expect(screen.getByText("Session CS-1")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Close Session" })).toBeInTheDocument();
  });

  test("permission error state renders", async () => {
    localStorage.setItem("counteros_token", "TOKEN");
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/auth/me")) return ok({ user, login_session_id: "1", expires_at: "2026-01-01T12:00:00Z" });
      return fail("AUTH_PERMISSION_DENIED", "Permission denied.");
    });

    render(<DashboardScreen />);

    await waitFor(() => expect(screen.getByText("Permission denied")).toBeInTheDocument());
  });

  test("API unavailable state renders", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("fetch failed"));

    render(<DashboardScreen />);

    await waitFor(() => expect(screen.getByText("API unavailable")).toBeInTheDocument());
  });
});

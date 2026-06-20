import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { StartupScreen } from "@/app/startup/StartupScreen";

vi.mock("next/link", () => ({
  default: ({ href, children, className }: { href: string; children: React.ReactNode; className?: string }) => (
    <a href={href} className={className}>
      {children}
    </a>
  )
}));

describe("StartupScreen", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  test("renders startup status from backend APIs", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/startup/status")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              success: true,
              data: {
                startup_status: "ready",
                api_status: "ok",
                database_status: "not_configured",
                recovery_required: false,
                migration_status: "not_configured",
                device_status: "not_configured",
                license_status: "not_configured",
                tenant_status: "not_configured",
                printer_status: "not_configured",
                sync_status: "not_configured",
                app_version: "0.1.0",
                backend_version: "0.1.0",
                frontend_version: "0.1.0",
                database_version: "not_configured"
              },
              request_id: "REQ-TEST"
            })
          )
        );
      }
      if (url.endsWith("/api/v1/health/version")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              success: true,
              data: {
                api_version: "v1",
                app_version: "0.1.0",
                backend_version: "0.1.0",
                frontend_version: "0.1.0",
                database_version: "not_configured",
                environment: "development"
              },
              request_id: "REQ-TEST"
            })
          )
        );
      }
      return Promise.resolve(
        new Response(
          JSON.stringify({
            success: true,
            data: {
              status: "ok",
              api: "ok",
              database: "not_configured",
              sync: "not_configured",
              printer: "not_configured",
              storage: "not_configured",
              license: "not_configured",
              device: "not_configured",
              tenant: "not_configured",
              migration: "not_configured",
              unsynced_event_count: 0,
              failed_event_count: 0,
              last_sync_at: null,
              last_backup_at: null
            },
            request_id: "REQ-TEST"
          })
        )
      );
    });

    render(<StartupScreen />);

    expect(screen.getByText("Checking local appliance status.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("Startup status")).toBeInTheDocument());
    expect(screen.getByText("ready")).toBeInTheDocument();
    expect(screen.getAllByText("not_configured").length).toBeGreaterThan(0);
    expect(screen.getByText("API v1")).toBeInTheDocument();
  });

  test("renders API unavailable state when backend cannot be reached", async () => {
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("fetch failed"));

    render(<StartupScreen />);

    await waitFor(() => expect(screen.getByText("Local API unavailable")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open Support" })).toHaveAttribute("href", "/system/support-required");
  });
});

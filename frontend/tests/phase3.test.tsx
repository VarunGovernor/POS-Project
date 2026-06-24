import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { CatalogScreen } from "@/app/catalog/CatalogScreen";
import { NewPatientScreen } from "@/app/patients/new/NewPatientScreen";
import { PatientsScreen } from "@/app/patients/PatientsScreen";

const push = vi.fn();
const back = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, back })
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
  return Promise.resolve(
    new Response(JSON.stringify({ success: false, error: { code, message, details: {} }, request_id: "REQ-TEST" }))
  );
}

describe("Phase 3 screens", () => {
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
    back.mockReset();
    localStorage.setItem("counteros_token", "TOKEN");
  });

  test("patients screen renders empty state", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() =>
      ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false })
    );

    render(<PatientsScreen />);

    await waitFor(() => expect(screen.getByText("No patients found.")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "New Patient" })).toHaveAttribute("href", "/patients/new");
  });

  test("patient create screen renders", () => {
    render(<NewPatientScreen />);

    expect(screen.getByRole("heading", { name: "New Patient" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create Patient" })).toBeInTheDocument();
  });

  test("catalog screen renders seeded service", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/api/v1/catalog/services")) {
        return ok({
          items: [
            {
              id: "1",
              service_code: "OP-CONSULT",
              service_name: "OP Consultation",
              service_type: "op",
              department_id: "1",
              department_name: "General Medicine",
              default_price: 500,
              currency: "INR",
              catalog_version: "CAT-DEV-001",
              price_version: "PRICE-DEV-001",
              status: "active"
            }
          ],
          page: 1,
          page_size: 25,
          total: 1,
          has_next: false
        });
      }
      if (url.includes("/api/v1/catalog/departments")) return ok({ items: [{ id: "1", department_code: "GEN-MED", department_name: "General Medicine", status: "active" }] });
      if (url.includes("/api/v1/catalog/doctors")) return ok({ items: [{ id: "1", doctor_code: "DR-GEN-1", full_name: "Dr. Dev General", specialization: "General Medicine", department_id: "1", department_name: "General Medicine", status: "active" }] });
      return ok({ items: [{ id: "1", master_type: "services", version_code: "DEV-001", last_successful_sync_at: null, status: "local_seeded" }] });
    });

    render(<CatalogScreen />);

    await waitFor(() => expect(screen.getByText("OP Consultation")).toBeInTheDocument());
    expect(screen.getByText("1 departments, 1 doctors, 1 master states.")).toBeInTheDocument();
  });

  test("catalog empty state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/api/v1/catalog/services")) return ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false });
      return ok({ items: [] });
    });

    render(<CatalogScreen />);

    await waitFor(() => expect(screen.getByText("No services found.")).toBeInTheDocument());
  });

  test("permission and API error states render", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() => fail("AUTH_PERMISSION_DENIED", "Permission denied."));
    render(<PatientsScreen />);
    await waitFor(() => expect(screen.getByText("Permission denied.")).toBeInTheDocument());

    vi.restoreAllMocks();
    vi.spyOn(global, "fetch").mockRejectedValue(new TypeError("fetch failed"));
    render(<CatalogScreen />);
    await waitFor(() => expect(screen.getByText("API unavailable.")).toBeInTheDocument());
  });
});

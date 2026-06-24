import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { RegistrationCenterScreen } from "@/app/registrations/RegistrationCenterScreen";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push })
}));

function ok(data: unknown) {
  return Promise.resolve(new Response(JSON.stringify({ success: true, data, request_id: "REQ-TEST" })));
}

const registration = {
  id: "1",
  registration_number: "OP-1001",
  registration_type: "op",
  patient_id: null,
  patient_name: "Ravi Kumar",
  mobile_number: "9876543210",
  age_years: 42,
  gender: "male",
  department_id: "1",
  department_name: "General Medicine",
  doctor_id: "1",
  doctor_name: "Dr. Sharma",
  visit_type: "new",
  token_number: "T-1001",
  admission_number: null,
  ward: null,
  room_or_bed: null,
  attender_name: null,
  deposit_amount: null,
  priority: null,
  sample_status: null,
  prescription_reference: null,
  status: "registered",
  billing_status: "ready_for_billing",
  notes: "Fever",
  created_at: "2026-06-24T00:00:00Z",
  updated_at: "2026-06-24T00:00:00Z"
};

describe("Phase 13 registration UI", () => {
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
    localStorage.setItem("counteros_token", "TOKEN");
  });

  test("registration center renders loading skeleton, OP/IP tabs, list, and form", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/api/v1/registrations")) return ok({ items: [registration], page: 1, page_size: 25, total: 1, has_next: false });
      if (url.includes("/api/v1/catalog/departments")) return ok({ items: [{ id: "1", department_code: "GEN", department_name: "General Medicine", status: "active" }] });
      return ok({ items: [{ id: "1", doctor_code: "DR", full_name: "Dr. Sharma", specialization: "General", department_id: "1", department_name: "General Medicine", status: "active" }] });
    });

    render(<RegistrationCenterScreen />);

    expect(screen.getByLabelText("Loading registrations")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText("Ravi Kumar").length).toBeGreaterThan(0));
    expect(screen.getByRole("button", { name: "OP Registration" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "IP Registration" })).toBeInTheDocument();
    expect(screen.getAllByText("New Registration").length).toBeGreaterThan(0);
  });

  test("send to billing stores context and routes", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.includes("/send-to-billing") && init?.method === "POST") return ok({ registration: { ...registration, billing_status: "sent_to_billing" }, billing_context: { registration_id: "1", registration_number: "OP-1001", registration_type: "op", patient_name: "Ravi Kumar", patient_id: null, department_id: "1", doctor_id: "1", notes: "From OP Registration OP-1001" } });
      if (url.includes("/api/v1/registrations")) return ok({ items: [registration], page: 1, page_size: 25, total: 1, has_next: false });
      if (url.includes("/api/v1/catalog/departments")) return ok({ items: [] });
      return ok({ items: [] });
    });

    render(<RegistrationCenterScreen />);
    await waitFor(() => expect(screen.getAllByText("Ravi Kumar").length).toBeGreaterThan(0));
    await userEvent.click(screen.getByRole("button", { name: "Send to Billing" }));

    expect(localStorage.getItem("counteros_billing_context")).toContain("OP-1001");
    expect(push).toHaveBeenCalledWith("/billing/new?from=registration");
  });
});

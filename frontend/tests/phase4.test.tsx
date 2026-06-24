import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { DraftListScreen } from "@/app/billing/drafts/DraftListScreen";
import { DraftWorkspaceScreen } from "@/app/billing/drafts/[draftId]/DraftWorkspaceScreen";
import { NewBillScreen } from "@/app/billing/new/NewBillScreen";

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

const patient = { id: "1", patient_number: "P-0001", full_name: "Ravi Kumar", phone: "9999999999", gender: "male", age_years: 35, sync_status: "pending" };
const department = { id: "1", department_code: "GEN-MED", department_name: "General Medicine", status: "active" };
const doctor = { id: "1", doctor_code: "DR-GEN-1", full_name: "Dr. Dev General", specialization: "General Medicine", department_id: "1", department_name: "General Medicine", status: "active" };
const service = { id: "1", service_code: "OP-CONSULT", service_name: "OP Consultation", service_type: "op", department_id: "1", department_name: "General Medicine", default_price: 500, currency: "INR", catalog_version: "CAT-DEV-001", price_version: "PRICE-DEV-001", status: "active" };
const draft = { id: "1", draft_number: "DRAFT-1", status: "draft", patient_name: "Ravi Kumar", bill_type: "op", total_amount: 0, subtotal_amount: 0, discount_amount: 0, tax_amount: 0, last_autosaved_at: "2026-01-01T00:00:00Z", items: [] };

describe("Phase 4 screens", () => {
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

  test("new bill screen renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/api/v1/sessions/current")) return ok({ session: { id: "1" } });
      if (url.includes("/api/v1/patients")) return ok({ items: [patient], page: 1, page_size: 25, total: 1, has_next: false });
      if (url.includes("/api/v1/catalog/departments")) return ok({ items: [department] });
      return ok({ items: [doctor] });
    });

    render(<NewBillScreen />);

    await waitFor(() => expect(screen.getByRole("button", { name: "Create Draft" })).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "← Back" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByText("Ravi Kumar")).toBeInTheDocument();
  });

  test("new bill uses registration billing context", async () => {
    localStorage.setItem("counteros_billing_context", JSON.stringify({ registration_id: "10", registration_number: "OP-1010", registration_type: "op", patient_name: "Registration Patient", patient_id: null, mobile_number: "999", department_id: "1", doctor_id: "1", department_name: "General Medicine", doctor_name: "Dr. Dev General", token_number: "T-1010", notes: "From OP Registration OP-1010" }));
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.includes("/api/v1/sessions/current")) return ok({ session: { id: "1" } });
      if (url.includes("/api/v1/patients") && init?.method === "POST") return ok({ patient });
      if (url.includes("/api/v1/patients")) return ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false });
      if (url.includes("/api/v1/catalog/departments")) return ok({ items: [department] });
      if (url.includes("/api/v1/bills/drafts")) return ok({ draft });
      return ok({ items: [doctor] });
    });

    render(<NewBillScreen />);
    await waitFor(() => expect(screen.getByText("Billing from Registration")).toBeInTheDocument());
    expect(screen.getByText(/Token T-1010/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Create Draft" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/bills/drafts",
      expect.objectContaining({ method: "POST" })
    ));
    expect(push).toHaveBeenCalledWith("/billing/drafts/1");
  });

  test("new bill shows IP and emergency registration context", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/api/v1/sessions/current")) return ok({ session: { id: "1" } });
      if (url.includes("/api/v1/patients")) return ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false });
      if (url.includes("/api/v1/catalog/departments")) return ok({ items: [department] });
      return ok({ items: [doctor] });
    });

    localStorage.setItem("counteros_billing_context", JSON.stringify({ registration_id: "11", registration_number: "IP-1011", registration_type: "ip", patient_name: "IP Patient", patient_id: null, department_id: "1", doctor_id: "1", admission_number: "ADM-1011", ward: "ICU", room_or_bed: "Bed 3", deposit_amount: 5000, notes: "From IP Registration IP-1011" }));
    const { unmount } = render(<NewBillScreen />);
    await waitFor(() => expect(screen.getByText(/Admission ADM-1011/)).toBeInTheDocument());
    expect(screen.getByText(/Deposit INR 5000/)).toBeInTheDocument();
    unmount();

    localStorage.setItem("counteros_billing_context", JSON.stringify({ registration_id: "12", registration_number: "ER-1012", registration_type: "emergency", patient_name: "Unknown Patient", patient_id: null, department_id: "1", doctor_id: "1", priority: "high", notes: "From EMERGENCY Registration ER-1012" }));
    render(<NewBillScreen />);
    await waitFor(() => expect(screen.getByText(/Priority high/)).toBeInTheDocument());
  });

  test("new bill no active session state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/api/v1/sessions/current")) return ok({ session: null });
      return ok({ items: [] });
    });

    render(<NewBillScreen />);

    await waitFor(() => expect(screen.getByText("Open cashier session before creating a bill.")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Open Session" })).toHaveAttribute("href", "/session/open");
  });

  test("draft list screen renders empty and draft states", async () => {
    vi.spyOn(global, "fetch").mockImplementationOnce(() => ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false }));
    render(<DraftListScreen />);
    await waitFor(() => expect(screen.getByText("No drafts found.")).toBeInTheDocument());

    vi.restoreAllMocks();
    vi.spyOn(global, "fetch").mockImplementation(() => ok({ items: [draft], page: 1, page_size: 25, total: 1, has_next: false }));
    render(<DraftListScreen />);
    await waitFor(() => expect(screen.getByText("DRAFT-1")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Continue" })).toHaveAttribute("href", "/billing/drafts/1");
  });

  test("draft workspace renders empty items", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/api/v1/bills/drafts/1")) return ok({ draft });
      return ok({ items: [service], page: 1, page_size: 25, total: 1, has_next: false });
    });

    render(<DraftWorkspaceScreen draftId="1" />);

    await waitFor(() => expect(screen.getByText("No draft items.")).toBeInTheDocument());
  });

  test("add item flow calls API and edit/remove controls render", async () => {
    const item = { id: "1", service_id: "1", service_name_at_time: "OP Consultation", department_id_at_time: "1", department_name_at_time: "General Medicine", quantity: 1, unit_price_at_time: 500, gross_amount: 500, discount_amount: 0, tax_amount: 0, final_line_total: 500, catalog_version: "CAT-DEV-001", price_version: "PRICE-DEV-001" };
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.includes("/items") && init?.method === "POST") return ok({ item, totals: { subtotal_amount: 500, discount_amount: 0, tax_amount: 0, total_amount: 500 }, last_autosaved_at: "now" });
      if (url.includes("/api/v1/bills/drafts/1")) return ok({ draft: { ...draft, items: [item], total_amount: 500 } });
      return ok({ items: [service], page: 1, page_size: 25, total: 1, has_next: false });
    });

    render(<DraftWorkspaceScreen draftId="1" />);
    await waitFor(() => expect(screen.getAllByText("OP Consultation").length).toBeGreaterThan(0));
    await userEvent.click(screen.getByRole("button", { name: "Add Item" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/bills/drafts/1/items",
      expect.objectContaining({ method: "POST" })
    ));
    expect(screen.getByRole("button", { name: "+ Qty" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Remove" })).toBeInTheDocument();
  });
});

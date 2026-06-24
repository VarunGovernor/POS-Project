import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { BillDetailScreen } from "@/app/billing/bills/[billId]/BillDetailScreen";
import { ReceiptPreviewScreen } from "@/app/billing/bills/[billId]/receipt/ReceiptPreviewScreen";
import { BillListScreen } from "@/app/billing/bills/BillListScreen";
import { DraftWorkspaceScreen } from "@/app/billing/drafts/[draftId]/DraftWorkspaceScreen";

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
  return Promise.resolve(new Response(JSON.stringify({ success: false, error: { code, message, details: {} }, request_id: "REQ-TEST" })));
}

const item = { id: "1", service_id: "1", service_name_at_time: "OP Consultation", department_id_at_time: "1", department_name_at_time: "General Medicine", quantity: 1, unit_price_at_time: 500, gross_amount: 500, discount_amount: 0, tax_amount: 0, final_line_total: 500, catalog_version: "CAT-DEV-001", price_version: "PRICE-DEV-001" };
const draft = { id: "1", draft_number: "DRAFT-1", status: "draft", bill_type: "op", total_amount: 500, subtotal_amount: 500, discount_amount: 0, tax_amount: 0, last_autosaved_at: "now", items: [item] };
const service = { id: "1", service_code: "OP-CONSULT", service_name: "OP Consultation", service_type: "op", department_id: "1", department_name: "General Medicine", default_price: 500, currency: "INR", catalog_version: "CAT-DEV-001", price_version: "PRICE-DEV-001", status: "active" };
const bill = { id: "1", bill_number: "BILL-1", status: "finalized", currency: "INR", subtotal_amount: 500, discount_amount: 0, tax_amount: 0, total_amount: 500, sync_status: "pending", finalized_at: "now", patient_name: "Ravi Kumar", patient: { id: "1", full_name: "Ravi Kumar", phone: null }, items: [{ id: "1", service_name_at_time: "OP Consultation", quantity: 1, unit_price: 500, final_line_total: 500, catalog_version: "CAT-DEV-001", price_version: "PRICE-DEV-001" }], payment: { id: "1", payment_number: "PAY-1", payment_method: "cash", status: "paid", amount: 500, received_amount: 1000, change_amount: 500, paid_at: "now" }, receipt: { id: "1", receipt_number: "RCPT-1", status: "generated", receipt_type: "original", generated_at: "now" } };

describe("Phase 5 screens", () => {
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
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: { randomUUID: () => "IDEM-UI" } });
    vi.restoreAllMocks();
    push.mockReset();
    back.mockReset();
    localStorage.setItem("counteros_token", "TOKEN");
  });

  test("draft workspace shows finalize action and cash only", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => String(input).includes("/catalog/services") ? ok({ items: [service], page: 1, page_size: 25, total: 1, has_next: false }) : ok({ draft }));
    render(<DraftWorkspaceScreen draftId="1" />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Finalize Bill" })).toBeInTheDocument());
    expect(screen.getByText("Cash")).toBeInTheDocument();
    expect(screen.queryByText("card")).not.toBeInTheDocument();
  });

  test("finalize cash flow calls API with idempotency key", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      if (url.includes("/finalize")) return ok({ bill, payment: bill.payment, receipt: bill.receipt, sync_event: { id: "1", event_type: "BILL_FINALIZED", status: "pending" } });
      if (url.includes("/catalog/services")) return ok({ items: [service], page: 1, page_size: 25, total: 1, has_next: false });
      return ok({ draft });
    });
    render(<DraftWorkspaceScreen draftId="1" />);
    await waitFor(() => expect(screen.getByLabelText("Cash received")).toBeInTheDocument());
    await userEvent.type(screen.getByLabelText("Cash received"), "1000");
    await userEvent.click(screen.getByRole("button", { name: "Finalize Bill" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/billing/bills/1"));
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:8000/api/v1/bills/drafts/1/finalize",
      expect.objectContaining({ headers: expect.objectContaining({ "Idempotency-Key": "IDEM-UI" }) })
    );
  });

  test("finalize insufficient cash error renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/finalize")) return fail("PAYMENT_AMOUNT_INSUFFICIENT", "Cash received is less than bill total.");
      if (url.includes("/catalog/services")) return ok({ items: [service], page: 1, page_size: 25, total: 1, has_next: false });
      return ok({ draft });
    });
    render(<DraftWorkspaceScreen draftId="1" />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Finalize Bill" })).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Finalize Bill" }));
    await waitFor(() => expect(screen.getByText(/PAYMENT_AMOUNT_INSUFFICIENT/)).toBeInTheDocument());
  });

  test("bill list detail receipt render", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/v1/bills")) return ok({ items: [bill], page: 1, page_size: 25, total: 1, has_next: false });
      if (url.includes("/receipts/by-bill")) return ok({ receipt: { ...bill.receipt, receipt_payload: { hospital_or_organization_name: "Development Organization", patient_name: "Ravi Kumar", bill_number: "BILL-1", total_amount: 500, items: [{ service_name: "OP Consultation", quantity: 1, line_total: 500 }] } } });
      return ok({ bill });
    });
    render(<BillListScreen />);
    await waitFor(() => expect(screen.getByText("BILL-1")).toBeInTheDocument());
    render(<BillDetailScreen billId="1" />);
    await waitFor(() => expect(screen.getByText("RCPT-1")).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "View Receipt" })).toHaveAttribute("href", "/billing/bills/1/receipt");
    expect(screen.getByRole("link", { name: "Print Receipt" })).toHaveAttribute("href", "/receipts/1/print");
    render(<ReceiptPreviewScreen billId="1" />);
    await waitFor(() => expect(screen.getByText("Development Organization")).toBeInTheDocument());
  });
});

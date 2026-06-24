import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import { ReceiptPreviewScreen } from "@/app/billing/bills/[billId]/receipt/ReceiptPreviewScreen";
import { PrinterScreen } from "@/app/printer/PrinterScreen";
import { ReceiptPrintScreen } from "@/app/receipts/[receiptId]/print/ReceiptPrintScreen";

const push = vi.fn();
const back = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, back })
}));

function ok(data: unknown) {
  return Promise.resolve(new Response(JSON.stringify({ success: true, data, request_id: "REQ-TEST" })));
}

function fail(code: string, message: string) {
  return Promise.resolve(new Response(JSON.stringify({ success: false, error: { code, message, details: {} }, request_id: "REQ-TEST" })));
}

const status = {
  status: "active",
  printer: { id: "1", printer_code: "DEV-PRINTER", printer_name: "Development Printer", printer_type: "dev", connection_type: "dev", is_default: true, last_seen_at: "now" },
  queued_job_count: 0,
  failed_job_count: 1,
  last_printed_at: null
};
const job = { id: "1", job_number: "PRINT-1", job_type: "receipt_original", status: "failed", attempt_count: 1, printed_at: null, failure_message: "paper out" };
const receipt = {
  id: "1",
  receipt_number: "RCPT-1",
  status: "generated",
  receipt_type: "original",
  generated_at: "now",
  receipt_payload: { hospital_or_organization_name: "Development Organization", branch_name: "Main", counter_name: "OP", patient_name: "Ravi Kumar", bill_number: "BILL-1", receipt_number: "RCPT-1", total_amount: 500, received_amount: 500, change_amount: 0, items: [{ service_name: "OP Consultation", quantity: 1, unit_price: 500, line_total: 500 }], registration: { registration_number: "OP-1001", registration_type: "op", token_number: "T-1001" } }
};

describe("Phase 6 screens", () => {
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
    Object.defineProperty(window, "print", { configurable: true, value: vi.fn() });
    localStorage.setItem("counteros_token", "TOKEN");
  });

  test("printer screen renders status and jobs", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => String(input).includes("/status") ? ok(status) : ok({ items: [job], page: 1, page_size: 25, total: 1, has_next: false }));
    render(<PrinterScreen />);
    await waitFor(() => expect(screen.getByText("Local Printer")).toBeInTheDocument());
    expect(screen.getByText("paper out")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  test("printer not configured state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => String(input).includes("/status") ? ok({ ...status, status: "not_configured", printer: null }) : ok({ items: [], page: 1, page_size: 25, total: 0, has_next: false }));
    render(<PrinterScreen />);
    await waitFor(() => expect(screen.getByText("Printer not configured.")).toBeInTheDocument());
  });

  test("receipt preview print and reprint call real APIs", async () => {
    const fetchMock = vi.spyOn(global, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.includes("/print") || url.includes("/reprint")) return ok({ job: { ...job, status: "printed", failure_message: null } });
      return ok({ receipt });
    });
    render(<ReceiptPreviewScreen billId="1" />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Print Receipt" })).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Print Receipt" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/receipts/1/print", expect.objectContaining({ method: "POST" })));
    expect(window.print).toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Reprint Receipt" }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/api/v1/receipts/1/reprint", expect.objectContaining({ method: "POST" })));
  });

  test("print receipt page renders and opens browser print", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => String(input).includes("/print") ? ok({ job: { ...job, status: "printed", failure_message: null } }) : ok({ receipt }));
    render(<ReceiptPrintScreen receiptId="1" />);
    await waitFor(() => expect(screen.getByText("OP-1001")).toBeInTheDocument());
    expect(screen.getByText("Ravi Kumar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "← Back" }).closest(".no-print")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Dashboard" }).closest(".no-print")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Print Receipt" }).closest(".no-print")).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Print Receipt" }));
    await waitFor(() => expect(window.print).toHaveBeenCalled());
  });

  test("print failure state renders", async () => {
    vi.spyOn(global, "fetch").mockImplementation((input) => String(input).includes("/print") ? fail("PRINTER_NOT_CONFIGURED", "Printer is not configured.") : ok({ receipt }));
    render(<ReceiptPreviewScreen billId="1" />);
    await waitFor(() => expect(screen.getByRole("button", { name: "Print Receipt" })).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: "Print Receipt" }));
    await waitFor(() => expect(screen.getByText(/PRINTER_NOT_CONFIGURED/)).toBeInTheDocument());
  });
});

"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LoadingPanel } from "@/app/components/LoadingPanel";
import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { Receipt, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function ReceiptPrintScreen({ receiptId }: { receiptId: string }) {
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [message, setMessage] = useState("");
  const [jobStatus, setJobStatus] = useState("");

  useEffect(() => {
    localApi.receipt(token(), receiptId)
      .then((response) => setReceipt(response.data.receipt))
      .catch((error) => setMessage(error instanceof Error ? error.message : "Receipt load failed."));
  }, [receiptId]);

  async function print() {
    if (!receipt) return;
    try {
      const response = await localApi.printReceipt(token(), receipt.id);
      setJobStatus(response.data.job.status);
      setMessage("Receipt printed");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Print job failed.");
    }
    window.print();
  }

  async function reprint() {
    if (!receipt) return;
    try {
      const response = await localApi.reprintReceipt(token(), receipt.id, "Browser print duplicate copy");
      setJobStatus(response.data.job.status);
      setMessage("Reprint created");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reprint job failed.");
    }
    window.print();
  }

  if (!receipt) return message ? <main><section className="shell panel"><h1>Receipt</h1><p className="error-text">{message}</p></section></main> : <LoadingPanel title="Receipt" />;

  return (
    <main>
      <section className="shell panel print-shell">
        <div className="actions no-print">
          <ScreenNavActions />
          <button type="button" onClick={print}>Print Receipt</button>
          <button type="button" onClick={reprint}>Reprint Receipt</button>
          <Link className="button secondary" href="/printer">Printer Queue</Link>
        </div>
        {message ? <div className={`${message.includes("failed") ? "error-text" : "toast"} no-print`}>{message}</div> : null}
        {jobStatus ? <p className="no-print">Print job {jobStatus}</p> : null}
        <ReceiptPaper receipt={receipt} />
      </section>
    </main>
  );
}

export function ReceiptPaper({ receipt }: { receipt: Receipt }) {
  const p = receipt.receipt_payload;
  const registration = (p.registration ?? {}) as Record<string, unknown>;
  const items = p.items ?? [];

  return (
    <article className="receipt-paper">
      <header>
        <h1>HamTech POS OS</h1>
        <strong>{String(p.hospital_or_organization_name ?? "Hospital")}</strong>
        <p>{String(p.branch_name ?? "")} · {String(p.counter_name ?? "")}</p>
      </header>
      <section className="receipt-lines">
        <Line label="Receipt" value={receipt.receipt_number} />
        <Line label="Bill" value={String(p.bill_number ?? "")} />
        <Line label="Date" value={String(p.generated_at ?? receipt.generated_at)} />
        <Line label="Cashier" value={String(p.cashier_name ?? "")} />
      </section>
      <section className="receipt-lines">
        <Line label="Registration" value={String(registration.registration_number ?? "-")} />
        <Line label="Type" value={label(String(registration.registration_type ?? p.bill_type ?? ""))} />
        <Line label="Patient" value={String(p.patient_name ?? "")} />
        <Line label="Mobile" value={String(registration.mobile_number ?? "")} />
        <Line label="Department" value={String(p.department_name ?? registration.department_name ?? "")} />
        <Line label="Doctor" value={String(p.doctor_name ?? registration.doctor_name ?? "")} />
        <Line label="Token" value={String(registration.token_number ?? "")} />
        <Line label="Admission" value={String(registration.admission_number ?? "")} />
        <Line label="Ward/Bed" value={[registration.ward, registration.room_or_bed].filter(Boolean).join(" / ")} />
        <Line label="Priority" value={String(registration.priority ?? "")} />
      </section>
      <section>
        {items.map((item, index) => (
          <div className="receipt-item" key={index}>
            <span>{String(item.service_name)}</span>
            <span>{String(item.quantity)} x {money(item.unit_price)}</span>
            <strong>{money(item.line_total)}</strong>
          </div>
        ))}
      </section>
      <section className="receipt-lines totals">
        <Line label="Subtotal" value={money(p.subtotal_amount)} />
        <Line label="Discount" value={money(p.discount_amount)} />
        <Line label="Tax" value={money(p.tax_amount)} />
        <Line label="Total" value={money(p.total_amount)} />
        <Line label="Paid" value={money(p.received_amount ?? p.amount_paid)} />
        <Line label="Change" value={money(p.change_amount)} />
      </section>
      <footer>Thank you. Please keep this receipt for hospital records.</footer>
    </article>
  );
}

function Line({ label, value }: { label: string; value: string }) {
  if (!value || value === "null" || value === "undefined" || value === "-") return null;
  return <div className="receipt-line"><span>{label}</span><strong>{value}</strong></div>;
}

function money(value: unknown) {
  return `INR ${Number(value || 0).toFixed(2)}`;
}

function label(value: string) {
  return value.split("_").filter(Boolean).map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}

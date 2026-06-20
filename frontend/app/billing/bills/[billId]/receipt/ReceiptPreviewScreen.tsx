"use client";

import { useEffect, useState } from "react";

import { Receipt, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function ReceiptPreviewScreen({ billId }: { billId: string }) {
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    localApi.receiptByBill(token(), billId)
      .then((response) => setReceipt(response.data.receipt))
      .catch((error) => setMessage(error instanceof Error ? error.message : "Receipt load failed."));
  }, [billId]);

  if (message) return <main><section className="shell panel"><h1>Receipt</h1><p className="error-text">{message}</p></section></main>;
  if (!receipt) return <main><section className="shell panel"><h1>Receipt</h1><p>Loading.</p></section></main>;

  const payload = receipt.receipt_payload;
  return (
    <main>
      <section className="shell panel">
        <h1>{receipt.receipt_number}</h1>
        <p>{String(payload.hospital_or_organization_name)}</p>
        <p>{String(payload.patient_name)} · {String(payload.bill_number)}</p>
        <div className="status-grid">
          {(payload.items ?? []).map((item, index) => (
            <div className="status-item" key={index}>
              <span className="label">{String(item.service_name)}</span>
              <span className="value">{String(item.line_total)}</span>
              <p>Qty {String(item.quantity)}</p>
            </div>
          ))}
        </div>
        <div className="status-item"><span className="label">Total</span><span className="value">{String(payload.total_amount)}</span></div>
      </section>
    </main>
  );
}

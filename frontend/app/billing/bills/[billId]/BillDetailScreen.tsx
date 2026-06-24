"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { FinalBill, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function BillDetailScreen({ billId }: { billId: string }) {
  const [bill, setBill] = useState<FinalBill | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    localApi.bill(token(), billId)
      .then((response) => setBill(response.data.bill))
      .catch((error) => setMessage(error instanceof Error ? error.message : "Bill load failed."));
  }, [billId]);

  if (message) return <main><section className="shell panel"><h1>Bill</h1><p className="error-text">{message}</p></section></main>;
  if (!bill) return <main><section className="shell panel"><h1>Bill</h1><p>Loading.</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>{bill.bill_number}</h1><div className="actions screen-nav"><ScreenNavActions /><span className="value">{bill.sync_status}</span></div></div>
        <p>{bill.patient?.full_name}</p>
        <div className="status-grid">
          {(bill.items ?? []).map((item) => (
            <div className="status-item" key={item.id}>
              <span className="label">{item.service_name_at_time}</span>
              <span className="value">{item.final_line_total}</span>
              <p>Qty {item.quantity}</p>
            </div>
          ))}
        </div>
        <div className="status-grid">
          <div className="status-item"><span className="label">Total</span><span className="value">{bill.total_amount}</span></div>
          <div className="status-item"><span className="label">Payment</span><span className="value">{bill.payment?.payment_method}</span></div>
          <div className="status-item"><span className="label">Receipt</span><span className="value">{bill.receipt?.receipt_number}</span></div>
        </div>
        <div className="actions">
          <Link className="button secondary" href={`/billing/bills/${bill.id}/receipt`}>View Receipt</Link>
          {bill.receipt ? <Link className="button" href={`/receipts/${bill.receipt.id}/print`}>Print Receipt</Link> : null}
        </div>
      </section>
    </main>
  );
}

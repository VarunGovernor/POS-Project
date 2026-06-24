"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { Receipt, localApi } from "@/lib/api/client";
import { ReceiptPaper } from "@/app/receipts/[receiptId]/print/ReceiptPrintScreen";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function ReceiptPreviewScreen({ billId }: { billId: string }) {
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [message, setMessage] = useState("");
  const [jobStatus, setJobStatus] = useState("");

  useEffect(() => {
    localApi.receiptByBill(token(), billId)
      .then((response) => setReceipt(response.data.receipt))
      .catch((error) => setMessage(error instanceof Error ? error.message : "Receipt load failed."));
  }, [billId]);

  async function print() {
    if (!receipt) return;
    setMessage("");
    try {
      const response = await localApi.printReceipt(token(), receipt.id);
      setJobStatus(response.data.job.status);
      window.print();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Print failed.");
    }
  }

  async function reprint() {
    if (!receipt) return;
    setMessage("");
    try {
      const response = await localApi.reprintReceipt(token(), receipt.id, "Customer requested duplicate copy");
      setJobStatus(response.data.job.status);
      window.print();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Reprint failed.");
    }
  }

  if (!receipt) return <main><section className="shell panel"><h1>Receipt</h1><p>Loading.</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header no-print">
          <h1>{receipt.receipt_number}</h1>
          <div className="actions screen-nav"><ScreenNavActions /></div>
        </div>
        <ReceiptPaper receipt={receipt} />
        {message ? <p className="error-text">{message}</p> : null}
        {jobStatus ? <p>Print job {jobStatus}</p> : null}
        <div className="actions no-print">
          <Link className="button secondary" href={`/receipts/${receipt.id}/print`}>View Printable Receipt</Link>
          <button type="button" onClick={print}>Print Receipt</button>
          <button type="button" onClick={reprint}>Reprint Receipt</button>
        </div>
      </section>
    </main>
  );
}

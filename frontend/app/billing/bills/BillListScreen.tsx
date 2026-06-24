"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { LoadingPanel } from "@/app/components/LoadingPanel";
import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { FinalBill, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function BillListScreen() {
  const [bills, setBills] = useState<FinalBill[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    localApi.bills(token()).then((response) => {
      setBills(response.data.items);
      setState("ready");
    }).catch((error) => {
      const text = error instanceof Error ? error.message : "Bill load failed.";
      setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    });
  }, []);

  if (state === "loading") return <LoadingPanel title="Bills" />;

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Bills</h1><div className="actions screen-nav"><ScreenNavActions /></div></div>
        {state === "api-unavailable" ? <p className="error-text">API unavailable.</p> : null}
        {state === "error" ? <p className="error-text">{message}</p> : null}
        {state === "ready" && bills.length === 0 ? <p>No bills found.</p> : null}
        {state === "ready" && bills.length > 0 ? (
          <div className="status-grid">
            {bills.map((bill) => (
              <div className="status-item" key={bill.id}>
                <span className="label">{bill.bill_number}</span>
                <span className="value">{bill.patient_name ?? "Patient"}</span>
                <p>{bill.currency} {bill.total_amount}</p>
                <Link className="button secondary" href={`/billing/bills/${bill.id}`}>View Bill</Link>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}

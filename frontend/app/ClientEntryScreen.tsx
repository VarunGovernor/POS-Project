"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const verticals = [
  "Hospital POS",
  "Restaurant POS",
  "Gas Station POS",
  "Retail POS",
  "Pharmacy POS",
  "Laboratory POS",
  "Parking POS",
  "Ticketing POS",
  "School / College Fee Counter",
  "Service Billing POS"
];

export function ClientEntryScreen() {
  const router = useRouter();
  const [toast, setToast] = useState("");

  function open(name: string) {
    if (name === "Hospital POS") router.push("/login");
    else setToast("This POS vertical is planned for a future rollout.");
  }

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <div>
            <span className="chip">HamTech Innovations</span>
            <h1>HamTech POS OS</h1>
            <p>Select POS System</p>
          </div>
        </div>
        {toast ? <div className="toast">{toast}</div> : null}
        <div className="module-grid">
          {verticals.map((name) => {
            const ready = name === "Hospital POS";
            return (
              <button className={`module-card ${ready ? "primary featured" : "future"}`} key={name} type="button" onClick={() => open(name)}>
                <span className="label">{ready ? "Ready" : "Coming Soon"}</span>
                <span className="value">{name}</span>
                <p>{ready ? "Hospital registration, billing, receipts, printer, sync, recovery, and reports." : "Planned for a future rollout."}</p>
              </button>
            );
          })}
        </div>
      </section>
    </main>
  );
}

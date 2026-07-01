"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const verticals = [
  {
    name: "Hospital POS",
    pos: "hospital",
    description: "Hospital registration, OP/IP/Emergency billing, pharmacy walk-in, receipts, printer, sync, recovery, and reports."
  },
  {
    name: "Liquor Store POS",
    pos: "liquor",
    description: "Age-controlled counter sales, product lookup, stock checks, billing, and receipt workflow."
  },
  { name: "Restaurant POS" },
  { name: "Gas Station POS" },
  { name: "Retail POS" },
  { name: "Laboratory POS" },
  { name: "Parking POS" },
  { name: "Ticketing POS" },
  { name: "School / College Fee Counter" },
  { name: "Service Billing POS" }
];

export function ClientEntryScreen() {
  const router = useRouter();
  const [toast, setToast] = useState("");

  function open(item: (typeof verticals)[number]) {
    if (item.pos) router.push(`/login?pos=${item.pos}`);
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
          {verticals.map((item) => {
            const ready = Boolean(item.pos);
            return (
              <button className={`module-card ${ready ? "primary featured" : "future"}`} key={item.name} type="button" onClick={() => open(item)}>
                <span className="label">{ready ? "Ready" : "Coming Soon"}</span>
                <span className="value">{item.name}</span>
                <p>{item.description ?? "Planned for a future rollout."}</p>
              </button>
            );
          })}
        </div>
      </section>
    </main>
  );
}

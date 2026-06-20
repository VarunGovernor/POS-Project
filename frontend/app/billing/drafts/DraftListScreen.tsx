"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { BillDraft, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function DraftListScreen() {
  const [drafts, setDrafts] = useState<BillDraft[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "error">("loading");
  const [message, setMessage] = useState("");

  async function load() {
    setState("loading");
    try {
      const response = await localApi.drafts(token());
      setDrafts(response.data.items);
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Draft load failed.";
      setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Drafts</h1><Link className="button" href="/billing/new">New Bill</Link></div>
        {state === "loading" ? <p>Loading.</p> : null}
        {state === "api-unavailable" ? <p className="error-text">API unavailable.</p> : null}
        {state === "error" ? <p className="error-text">{message}</p> : null}
        {state === "ready" && drafts.length === 0 ? <p>No drafts found.</p> : null}
        {state === "ready" && drafts.length > 0 ? (
          <div className="status-grid">
            {drafts.map((draft) => (
              <div className="status-item" key={draft.id}>
                <span className="label">{draft.draft_number}</span>
                <span className="value">{draft.patient_name ?? "No patient"}</span>
                <p>Total {draft.total_amount}</p>
                <Link className="button secondary" href={`/billing/drafts/${draft.id}`}>Continue</Link>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}

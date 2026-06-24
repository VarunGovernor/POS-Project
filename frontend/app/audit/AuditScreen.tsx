"use client";

import { useEffect, useState } from "react";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { AuditLog, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function AuditScreen() {
  const [items, setItems] = useState<AuditLog[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "permission-denied" | "error">("loading");
  const [message, setMessage] = useState("");

  async function load() {
    setState("loading");
    try {
      setItems((await localApi.auditLogs(token())).data.items);
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Audit load failed.";
      if (text.includes("AUTH_PERMISSION_DENIED")) setState("permission-denied");
      else setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") return <main><section className="shell panel"><h1>Audit</h1><p>Loading.</p></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Audit</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "permission-denied") return <main><section className="shell panel"><h1>Audit</h1><p className="error-text">Permission denied.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>Audit</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Audit</h1><div className="actions screen-nav"><ScreenNavActions /><button type="button" onClick={load}>Refresh</button></div></div>
        {items.length === 0 ? <p>No audit logs.</p> : null}
        <div className="status-grid">
          {items.map((item) => (
            <div className="status-item" key={item.id}>
              <span className="label">{item.action}</span>
              <span className="value">{item.severity}</span>
              <p>{item.entity_type ?? "system"} {item.entity_id ?? ""}</p>
              <p>{item.created_at}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

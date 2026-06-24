"use client";

import { useEffect, useState } from "react";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { RecoveryMarker, RecoveryStatus, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function RecoveryScreen() {
  const [status, setStatus] = useState<RecoveryStatus | null>(null);
  const [items, setItems] = useState<RecoveryMarker[]>([]);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "permission-denied" | "error">("loading");

  async function load() {
    setState("loading");
    setMessage("");
    try {
      const [statusResponse, itemsResponse] = await Promise.all([
        localApi.recoveryStatus(token()),
        localApi.recoveryItems(token())
      ]);
      setStatus(statusResponse.data);
      setItems(itemsResponse.data.items);
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Recovery load failed.";
      if (text.includes("AUTH_PERMISSION_DENIED")) setState("permission-denied");
      else setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  async function scan() {
    try {
      await localApi.recoveryScan(token());
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Scan failed.");
    }
  }

  async function resolve(markerId: string) {
    try {
      await localApi.recoveryResolve(token(), markerId);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Resolve failed.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") return <main><section className="shell panel"><h1>Recovery</h1><p>Loading.</p></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Recovery</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "permission-denied") return <main><section className="shell panel"><h1>Recovery</h1><p className="error-text">Permission denied.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>Recovery</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <h1>Recovery</h1>
          <div className="actions screen-nav"><ScreenNavActions /><span className="value">{status?.recovery_required ? "required" : "ok"}</span></div>
        </div>
        {message ? <p className="error-text">{message}</p> : null}
        <div className="status-grid">
          <div className="status-item"><span className="label">Open markers</span><span className="value">{status?.open_marker_count}</span></div>
          <div className="status-item"><span className="label">Critical</span><span className="value">{status?.critical_count}</span></div>
          <div className="status-item"><span className="label">Warning</span><span className="value">{status?.warning_count}</span></div>
          <div className="status-item"><span className="label">Info</span><span className="value">{status?.info_count}</span></div>
        </div>
        <div className="actions"><button type="button" onClick={scan}>Scan</button></div>
        {items.length === 0 ? <p>No recovery work items.</p> : null}
        <div className="status-grid">
          {items.map((item) => (
            <div className="status-item" key={item.id}>
              <span className="label">{item.marker_type}</span>
              <span className="value">{item.severity}</span>
              <p>{item.title}</p>
              <p>{item.description}</p>
              {item.status === "open" ? <button type="button" onClick={() => resolve(item.id)}>Acknowledge</button> : null}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

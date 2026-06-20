"use client";

import { useEffect, useState } from "react";

import { SupportStatus, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function SupportScreen() {
  const [status, setStatus] = useState<SupportStatus | null>(null);
  const [bundle, setBundle] = useState("");
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "permission-denied" | "error">("loading");

  async function load() {
    setState("loading");
    setMessage("");
    try {
      setStatus((await localApi.supportStatus(token())).data);
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Support load failed.";
      if (text.includes("AUTH_PERMISSION_DENIED")) setState("permission-denied");
      else setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  async function createBundle() {
    try {
      setBundle((await localApi.supportBundle(token())).data.bundle.bundle_id);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Bundle failed.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") return <main><section className="shell panel"><h1>Support</h1><p>Loading.</p></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Support</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "permission-denied") return <main><section className="shell panel"><h1>Support</h1><p className="error-text">Permission denied.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>Support</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Support</h1><button type="button" onClick={load}>Refresh</button></div>
        {message ? <p className="error-text">{message}</p> : null}
        <div className="status-grid">
          {status ? Object.entries(status).map(([key, value]) => (
            <div className="status-item" key={key}><span className="label">{key}</span><span className="value">{String(value)}</span></div>
          )) : null}
        </div>
        <div className="actions"><button type="button" onClick={createBundle}>Create Bundle</button></div>
        {bundle ? <p>Bundle created: {bundle}</p> : null}
      </section>
    </main>
  );
}

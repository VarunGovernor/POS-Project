"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CashierSession, DeviceStatusData, MeData, localApi } from "@/lib/api/client";

type State =
  | { name: "loading" }
  | { name: "success"; me: MeData; device: DeviceStatusData; session: CashierSession | null }
  | { name: "permission-denied"; message: string }
  | { name: "api-unavailable" }
  | { name: "error"; message: string };

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function DashboardScreen() {
  const router = useRouter();
  const [state, setState] = useState<State>({ name: "loading" });
  const [toast, setToast] = useState("");

  async function load() {
    setState({ name: "loading" });
    try {
      const authToken = token();
      const [me, device, session] = await Promise.all([
        localApi.me(authToken),
        localApi.deviceStatus(authToken),
        localApi.currentSession(authToken)
      ]);
      setState({ name: "success", me: me.data, device: device.data, session: session.data.session });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Dashboard load failed.";
      if (message.includes("AUTH_PERMISSION_DENIED")) setState({ name: "permission-denied", message });
      else if (message.toLowerCase().includes("fetch")) setState({ name: "api-unavailable" });
      else setState({ name: "error", message });
    }
  }

  async function logout() {
    await localApi.logout(token());
    localStorage.removeItem("counteros_token");
    router.push("/login");
  }

  useEffect(() => {
    const pendingToast = sessionStorage.getItem("counteros_toast");
    sessionStorage.removeItem("counteros_toast");
    setToast(pendingToast ?? "");
    void load();
  }, []);

  if (state.name === "loading") return <main><section className="shell panel"><h1>Dashboard</h1><div className="status-grid" aria-label="Loading dashboard"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div></section></main>;
  if (state.name === "api-unavailable") return <main><section className="shell panel"><h1>API unavailable</h1><button onClick={load}>Refresh</button></section></main>;
  if (state.name === "permission-denied") return <main><section className="shell panel"><h1>Permission denied</h1><p className="error-text">{state.message}</p></section></main>;
  if (state.name === "error") return <main><section className="shell panel"><h1>Dashboard error</h1><p className="error-text">{state.message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <div>
            <span className="chip">Hospital POS</span>
            <h1>Dashboard</h1>
          </div>
          <div className="actions">
            <button type="button" onClick={load}>Refresh</button>
            <button type="button" onClick={logout}>Logout</button>
          </div>
        </div>
        {toast ? <div className="toast">{toast}</div> : null}
        <div className="status-grid">
          <div className="status-item"><span className="label">User</span><span className="value">{state.me.user.display_name}</span></div>
          <div className="status-item"><span className="label">Device</span><span className="value">{clientDevice(state.device.device_name)}</span></div>
          <div className="status-item"><span className="label">Counter</span><span className="value">{clientCounter(state.device.counter_name)}</span></div>
          <div className="status-item"><span className="label">Cashier session</span><span className="value">{state.session ? state.session.status : "none"}</span></div>
        </div>
        <div className="actions">
          {!state.session ? <Link className="button" href="/session/open">Open Session</Link> : null}
          {state.session ? <Link className="button" href="/session/close">Close Session</Link> : null}
        </div>
        <div className="module-grid">
          <Module href="/registrations" title="Registration Center" text="OP, IP, emergency, follow-up, lab, pharmacy walk-in" primary featured />
          <Module href="/patients" title="Patient Lookup" text="Find or create patient records" />
          <Module href="/billing/new" title="New Bill" text="Create a draft bill" primary />
          <Module href="/billing/drafts" title="Drafts" text="Resume draft bills" />
          <Module href="/billing/bills" title="Bills" text="Final bills and receipts" />
          <Module href="/printer" title="Printer" text="Receipt printer queue" />
          <Module href="/sync" title="Sync" text="Local sync status" />
          <Module href="/recovery" title="Recovery" text="Crash recovery work items" />
          <Module href="/reports" title="Reports" text="Daily collections" />
          <Module href="/settings" title="Settings" text="Device settings" />
          <Module href="/support" title="Support" text="Support bundle and health" />
          <Module href="/audit" title="Audit" text="Local audit trail" />
        </div>
      </section>
    </main>
  );
}

function clientDevice(value: string) {
  return value.includes("Development") ? "POS Terminal" : value;
}

function clientCounter(value: string) {
  return value.includes("Development") ? "OP Counter 1" : value;
}

function Module({ href, title, text, primary = false, featured = false }: { href: string; title: string; text: string; primary?: boolean; featured?: boolean }) {
  return (
    <Link className={`module-card ${primary ? "primary" : ""} ${featured ? "featured" : ""}`} href={href}>
      <span className="label">{primary ? "Primary" : "Module"}</span>
      <span className="value">{title}</span>
      <p>{text}</p>
    </Link>
  );
}

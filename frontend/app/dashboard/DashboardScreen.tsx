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
    void load();
  }, []);

  if (state.name === "loading") return <main><section className="shell panel"><h1>Dashboard</h1><p>Loading.</p></section></main>;
  if (state.name === "api-unavailable") return <main><section className="shell panel"><h1>API unavailable</h1><button onClick={load}>Refresh</button></section></main>;
  if (state.name === "permission-denied") return <main><section className="shell panel"><h1>Permission denied</h1><p className="error-text">{state.message}</p></section></main>;
  if (state.name === "error") return <main><section className="shell panel"><h1>Dashboard error</h1><p className="error-text">{state.message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <h1>Dashboard</h1>
          <button type="button" onClick={load}>Refresh</button>
        </div>
        <div className="status-grid">
          <div className="status-item"><span className="label">User</span><span className="value">{state.me.user.display_name}</span></div>
          <div className="status-item"><span className="label">Device</span><span className="value">{state.device.device_name}</span></div>
          <div className="status-item"><span className="label">Counter</span><span className="value">{state.device.counter_name}</span></div>
          <div className="status-item"><span className="label">Cashier session</span><span className="value">{state.session ? state.session.status : "none"}</span></div>
        </div>
        <div className="actions">
          {!state.session ? <Link className="button" href="/session/open">Open Session</Link> : null}
          {state.session ? <Link className="button" href="/session/close">Close Session</Link> : null}
          <Link className="button secondary" href="/patients">Patient Lookup</Link>
          <Link className="button secondary" href="/catalog">Catalog Lookup</Link>
          <Link className="button" href="/billing/new">New Bill</Link>
          <Link className="button secondary" href="/billing/drafts">Drafts</Link>
          <Link className="button secondary" href="/billing/bills">Bills</Link>
          <button type="button" onClick={logout}>Logout</button>
        </div>
      </section>
    </main>
  );
}

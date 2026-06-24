"use client";

import { useEffect, useState } from "react";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { TodayReport, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function ReportsScreen() {
  const [today, setToday] = useState<TodayReport | null>(null);
  const [pending, setPending] = useState<Array<{ status: string; count: number }>>([]);
  const [departments, setDepartments] = useState<Array<{ department_name: string; bill_count: number; net_amount: number }>>([]);
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "permission-denied" | "error">("loading");
  const [message, setMessage] = useState("");

  async function load() {
    setState("loading");
    try {
      const authToken = token();
      const [todayResponse, pendingResponse, me] = await Promise.all([
        localApi.todayReport(authToken),
        localApi.pendingSyncReport(authToken),
        localApi.me(authToken)
      ]);
      setToday(todayResponse.data);
      setPending(pendingResponse.data.by_status);
      if (me.data.user.permissions.includes("report.department.view")) {
        setDepartments((await localApi.departmentReport(authToken)).data.items);
      }
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Reports load failed.";
      if (text.includes("AUTH_PERMISSION_DENIED")) setState("permission-denied");
      else setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") return <main><section className="shell panel"><h1>Reports</h1><p>Loading.</p></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Reports</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "permission-denied") return <main><section className="shell panel"><h1>Reports</h1><p className="error-text">Permission denied.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>Reports</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Reports</h1><div className="actions screen-nav"><ScreenNavActions /><button type="button" onClick={load}>Refresh</button></div></div>
        <div className="status-grid">
          <div className="status-item"><span className="label">Business date</span><span className="value">{today?.business_date}</span></div>
          <div className="status-item"><span className="label">Bills</span><span className="value">{today?.bill_count}</span></div>
          <div className="status-item"><span className="label">Net amount</span><span className="value">{today?.net_amount} {today?.currency}</span></div>
          <div className="status-item"><span className="label">Cash collected</span><span className="value">{today?.cash_collected} {today?.currency}</span></div>
          <div className="status-item"><span className="label">Receipts</span><span className="value">{today?.receipt_count}</span></div>
          <div className="status-item"><span className="label">Pending sync</span><span className="value">{today?.pending_sync_count}</span></div>
        </div>
        <h2>Pending Sync</h2>
        {pending.length === 0 ? <p>No sync events.</p> : pending.map((item) => <p key={item.status}>{item.status}: {item.count}</p>)}
        <h2>Departments</h2>
        {departments.length === 0 ? <p>No department collection data.</p> : departments.map((item) => <p key={item.department_name}>{item.department_name}: {item.net_amount}</p>)}
      </section>
    </main>
  );
}

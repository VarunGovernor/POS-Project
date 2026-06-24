"use client";

import { useEffect, useState } from "react";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { SyncConflict, SyncEvent, SyncStatus, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function SyncScreen() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [events, setEvents] = useState<SyncEvent[]>([]);
  const [conflicts, setConflicts] = useState<SyncConflict[]>([]);
  const [canRun, setCanRun] = useState(false);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "permission-denied" | "error">("loading");

  async function load() {
    setState("loading");
    setMessage("");
    try {
      const authToken = token();
      const me = await localApi.me(authToken);
      const [syncStatus, syncEvents] = await Promise.all([
        localApi.syncStatus(authToken),
        localApi.syncEvents(authToken)
      ]);
      setStatus(syncStatus.data);
      setEvents(syncEvents.data.items);
      setCanRun(me.data.user.permissions.includes("sync.run"));
      if (me.data.user.permissions.includes("sync.conflict.view")) {
        setConflicts((await localApi.syncConflicts(authToken)).data.items);
      } else {
        setConflicts([]);
      }
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Sync load failed.";
      if (text.includes("AUTH_PERMISSION_DENIED")) setState("permission-denied");
      else setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  async function retryAll() {
    try {
      await localApi.syncRetryAll(token());
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Retry failed.");
    }
  }

  async function retryEvent(eventId: string) {
    try {
      await localApi.syncRetryEvent(token(), eventId);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Retry failed.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") return <main><section className="shell panel"><h1>Sync</h1><p>Loading.</p></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Sync</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "permission-denied") return <main><section className="shell panel"><h1>Sync</h1><p className="error-text">Permission denied.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>Sync</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <h1>Sync</h1>
          <div className="actions screen-nav"><ScreenNavActions /><span className="value">{status?.status}</span></div>
        </div>
        {message ? <p className="error-text">{message}</p> : null}
        <div className="status-grid">
          <div className="status-item"><span className="label">Pending</span><span className="value">{status?.pending_count}</span></div>
          <div className="status-item"><span className="label">Failed</span><span className="value">{(status?.failed_retryable_count ?? 0) + (status?.failed_permanent_count ?? 0)}</span></div>
          <div className="status-item"><span className="label">Conflicts</span><span className="value">{status?.conflict_count}</span></div>
          <div className="status-item"><span className="label">Adapter</span><span className="value">{status?.adapter}</span></div>
          <div className="status-item"><span className="label">Last attempt</span><span className="value">{status?.last_attempt_at ?? "none"}</span></div>
          <div className="status-item"><span className="label">Last success</span><span className="value">{status?.last_successful_sync_at ?? "none"}</span></div>
        </div>
        {canRun ? <div className="actions"><button type="button" onClick={retryAll}>Retry All</button></div> : null}
        {events.length === 0 ? <p>No sync events.</p> : null}
        <div className="status-grid">
          {events.map((event) => (
            <div className="status-item" key={event.id}>
              <span className="label">{event.event_type}</span>
              <span className="value">{event.status}</span>
              <p>{event.entity_type} #{event.entity_id}</p>
              <p>Attempts: {event.attempt_count}</p>
              {["pending", "failed_retryable"].includes(event.status) ? <button type="button" onClick={() => retryEvent(event.id)}>Retry</button> : null}
            </div>
          ))}
        </div>
        <h2>Conflicts</h2>
        {conflicts.length === 0 ? <p>No sync conflicts.</p> : null}
        <div className="status-grid">
          {conflicts.map((conflict) => (
            <div className="status-item" key={conflict.id}>
              <span className="label">{conflict.conflict_type}</span>
              <span className="value">{conflict.resolution_status}</span>
              <p>{conflict.entity_type} #{conflict.entity_id}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

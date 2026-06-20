"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { HealthData, StartupStatusData, VersionData, localApi } from "@/lib/api/client";

type ScreenState =
  | { name: "loading" }
  | { name: "success"; startup: StartupStatusData; health: HealthData; version: VersionData }
  | { name: "api-unavailable" }
  | { name: "support-required"; message: string }
  | { name: "error"; message: string };

function StatusItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="status-item">
      <span className="label">{label}</span>
      <span className="value">{value}</span>
    </div>
  );
}

export function StartupScreen() {
  const [state, setState] = useState<ScreenState>({ name: "loading" });

  async function loadStatus() {
    setState({ name: "loading" });
    try {
      const [startup, health, version] = await Promise.all([
        localApi.startupStatus(),
        localApi.health(),
        localApi.version()
      ]);

      if (startup.data.startup_status === "support_required") {
        setState({ name: "support-required", message: "SUPPORT_REQUIRED" });
        return;
      }

      setState({
        name: "success",
        startup: startup.data,
        health: health.data,
        version: version.data
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Startup check failed.";
      if (message.toLowerCase().includes("fetch")) {
        setState({ name: "api-unavailable" });
        return;
      }
      setState({ name: "error", message });
    }
  }

  useEffect(() => {
    void loadStatus();
  }, []);

  if (state.name === "loading") {
    return (
      <main>
        <section className="shell panel" aria-live="polite">
          <h1>Startup</h1>
          <p>Checking local appliance status.</p>
        </section>
      </main>
    );
  }

  if (state.name === "api-unavailable") {
    return (
      <main>
        <section className="shell panel">
          <h1>Local API unavailable</h1>
          <p className="error-text">Cannot reach local backend API.</p>
          <div className="actions">
            <button type="button" onClick={loadStatus}>
              Retry
            </button>
            <Link className="button secondary" href="/system/support-required">
              Open Support
            </Link>
          </div>
        </section>
      </main>
    );
  }

  if (state.name === "support-required") {
    return (
      <main>
        <section className="shell panel">
          <h1>Support required</h1>
          <p className="error-text">{state.message}</p>
          <div className="actions">
            <button type="button" onClick={loadStatus}>
              Retry check
            </button>
          </div>
        </section>
      </main>
    );
  }

  if (state.name === "error") {
    return (
      <main>
        <section className="shell panel">
          <h1>Startup error</h1>
          <p className="error-text">{state.message}</p>
          <div className="actions">
            <button type="button" onClick={loadStatus}>
              Retry
            </button>
          </div>
        </section>
      </main>
    );
  }

  const { startup, version } = state;

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <h1>Startup</h1>
          <span className="value">API {version.api_version}</span>
        </div>
        <div className="status-grid">
          <StatusItem label="Startup status" value={startup.startup_status} />
          <StatusItem label="API status" value={startup.api_status} />
          <StatusItem label="Database status" value={startup.database_status} />
          <StatusItem label="Recovery required" value={startup.recovery_required ? "yes" : "no"} />
          <StatusItem label="Migration status" value={startup.migration_status} />
          <StatusItem label="Device status" value={startup.device_status} />
          <StatusItem label="License status" value={startup.license_status} />
          <StatusItem label="Printer status" value={startup.printer_status} />
          <StatusItem label="Sync status" value={startup.sync_status} />
          <StatusItem label="App version" value={startup.app_version} />
          <StatusItem label="Backend version" value={startup.backend_version} />
          <StatusItem label="Frontend version" value={startup.frontend_version} />
          <StatusItem label="Database version" value={startup.database_version} />
        </div>
      </section>
    </main>
  );
}

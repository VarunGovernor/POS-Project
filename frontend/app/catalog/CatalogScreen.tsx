"use client";

import { FormEvent, useEffect, useState } from "react";

import { LoadingPanel } from "@/app/components/LoadingPanel";
import { Department, Doctor, MasterSyncState, ServiceItem, localApi } from "@/lib/api/client";

type State =
  | { name: "loading" }
  | { name: "success"; services: ServiceItem[]; departments: Department[]; doctors: Doctor[]; syncState: MasterSyncState[] }
  | { name: "permission-denied"; message: string }
  | { name: "api-unavailable" }
  | { name: "error"; message: string };

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function CatalogScreen() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<State>({ name: "loading" });

  async function load(q = query) {
    setState({ name: "loading" });
    try {
      const authToken = token();
      const [services, departments, doctors, syncState] = await Promise.all([
        localApi.services(authToken, q),
        localApi.departments(authToken),
        localApi.doctors(authToken),
        localApi.masterSyncState(authToken)
      ]);
      setState({
        name: "success",
        services: services.data.items,
        departments: departments.data.items,
        doctors: doctors.data.items,
        syncState: syncState.data.items
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Catalog load failed.";
      if (message.includes("AUTH_PERMISSION_DENIED")) setState({ name: "permission-denied", message });
      else if (message.toLowerCase().includes("fetch")) setState({ name: "api-unavailable" });
      else setState({ name: "error", message });
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void load(query);
  }

  useEffect(() => {
    void load("");
  }, []);

  if (state.name === "loading") return <LoadingPanel title="Catalog" />;

  return (
    <main>
      <section className="shell panel">
        <h1>Catalog</h1>
        <form onSubmit={submit} className="form-grid">
          <label><span className="label">Service search</span><input value={query} onChange={(event) => setQuery(event.target.value)} /></label>
          <div className="actions"><button type="submit">Search</button></div>
        </form>
        {state.name === "api-unavailable" ? <p className="error-text">API unavailable.</p> : null}
        {state.name === "permission-denied" ? <p className="error-text">Permission denied.</p> : null}
        {state.name === "error" ? <p className="error-text">{state.message}</p> : null}
        {state.name === "success" && state.services.length === 0 ? <p>No services found.</p> : null}
        {state.name === "success" ? (
          <>
            <div className="status-grid">
              {state.services.map((service) => (
                <div className="status-item" key={service.id}>
                  <span className="label">{service.service_code}</span>
                  <span className="value">{service.service_name}</span>
                  <p>{service.currency} {service.default_price}</p>
                </div>
              ))}
            </div>
            <p>{state.departments.length} departments, {state.doctors.length} doctors, {state.syncState.length} master states.</p>
          </>
        ) : null}
      </section>
    </main>
  );
}

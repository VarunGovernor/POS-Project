"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { Patient, localApi } from "@/lib/api/client";

type State =
  | { name: "loading" }
  | { name: "success"; patients: Patient[] }
  | { name: "permission-denied"; message: string }
  | { name: "api-unavailable" }
  | { name: "error"; message: string };

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function PatientsScreen() {
  const [query, setQuery] = useState("");
  const [state, setState] = useState<State>({ name: "loading" });

  async function load(q = query) {
    setState({ name: "loading" });
    try {
      const response = await localApi.patients(token(), q);
      setState({ name: "success", patients: response.data.items });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Patient lookup failed.";
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

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <h1>Patients</h1>
          <div className="actions screen-nav">
            <ScreenNavActions />
            <Link className="button" href="/patients/new">New Patient</Link>
          </div>
        </div>
        <form onSubmit={submit} className="form-grid">
          <label><span className="label">Search</span><input value={query} onChange={(event) => setQuery(event.target.value)} /></label>
          <div className="actions"><button type="submit">Search</button></div>
        </form>
        {state.name === "loading" ? <p>Loading.</p> : null}
        {state.name === "api-unavailable" ? <p className="error-text">API unavailable.</p> : null}
        {state.name === "permission-denied" ? <p className="error-text">Permission denied.</p> : null}
        {state.name === "error" ? <p className="error-text">{state.message}</p> : null}
        {state.name === "success" && state.patients.length === 0 ? <p>No patients found.</p> : null}
        {state.name === "success" && state.patients.length > 0 ? (
          <div className="status-grid">
            {state.patients.map((patient) => (
              <div className="status-item" key={patient.id}>
                <span className="label">{patient.patient_number}</span>
                <span className="value">{patient.full_name}</span>
                <p>{patient.phone ?? "No phone"}</p>
              </div>
            ))}
          </div>
        ) : null}
      </section>
    </main>
  );
}

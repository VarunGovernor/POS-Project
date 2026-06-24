"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { Department, Doctor, Registration, RegistrationType, localApi } from "@/lib/api/client";

const tabs: Array<{ type: RegistrationType; label: string }> = [
  { type: "op", label: "OP Registration" },
  { type: "ip", label: "IP Registration" },
  { type: "emergency", label: "Emergency" },
  { type: "follow_up", label: "Follow-up" },
  { type: "lab", label: "Lab" },
  { type: "pharmacy_walkin", label: "Pharmacy Walk-in" }
];

type State = "loading" | "ready" | "permission-denied" | "api-unavailable" | "error";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

function emptyForm(type: RegistrationType) {
  return {
    registration_type: type,
    patient_name: type === "emergency" ? "Unknown Patient" : "",
    mobile_number: "",
    age_years: "",
    gender: "",
    department_id: "",
    doctor_id: "",
    visit_type: type === "follow_up" ? "follow_up" : "new",
    ward: "",
    room_or_bed: "",
    attender_name: "",
    deposit_amount: "",
    priority: type === "emergency" ? "high" : "",
    sample_status: type === "lab" ? "sample_pending" : "",
    prescription_reference: "",
    notes: ""
  };
}

export function RegistrationCenterScreen() {
  const router = useRouter();
  const [activeType, setActiveType] = useState<RegistrationType>("op");
  const [query, setQuery] = useState("");
  const [registrations, setRegistrations] = useState<Registration[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [form, setForm] = useState(emptyForm("op"));
  const [state, setState] = useState<State>("loading");
  const [message, setMessage] = useState("");
  const [toast, setToast] = useState("");
  const [saving, setSaving] = useState(false);

  const selected = registrations.find((item) => item.id === selectedId) ?? registrations[0] ?? null;
  const metrics = useMemo(() => ({
    today: registrations.length,
    op: registrations.filter((item) => item.registration_type === "op").length,
    ip: registrations.filter((item) => item.registration_type === "ip").length,
    ready: registrations.filter((item) => item.billing_status === "ready_for_billing").length,
    pending: registrations.filter((item) => item.billing_status === "pending").length
  }), [registrations]);

  async function load(type = activeType, q = query) {
    setState("loading");
    try {
      const authToken = token();
      const [registrationList, departmentList, doctorList] = await Promise.all([
        localApi.registrations(authToken, { registration_type: type, q }),
        localApi.departments(authToken),
        localApi.doctors(authToken)
      ]);
      setRegistrations(registrationList.data.items);
      setDepartments(departmentList.data.items);
      setDoctors(doctorList.data.items);
      setSelectedId(registrationList.data.items[0]?.id ?? "");
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Registration load failed.";
      if (text.includes("AUTH_PERMISSION_DENIED")) setState("permission-denied");
      else if (text.toLowerCase().includes("fetch")) setState("api-unavailable");
      else setState("error");
      setMessage(text);
    }
  }

  function switchType(type: RegistrationType) {
    setActiveType(type);
    setForm(emptyForm(type));
    void load(type, "");
  }

  function setField(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      const payload: Record<string, unknown> = Object.fromEntries(Object.entries(form).filter(([, value]) => value !== ""));
      if (payload.age_years) payload.age_years = Number(payload.age_years);
      if (payload.deposit_amount) payload.deposit_amount = Number(payload.deposit_amount);
      const created = await localApi.createRegistration(token(), payload);
      await load(activeType, query);
      setSelectedId(created.data.registration.id);
      setToast(`${created.data.registration.registration_number} created`);
      setForm(emptyForm(activeType));
    } catch (error) {
      setToast(error instanceof Error ? error.message : "Registration create failed.");
    } finally {
      setSaving(false);
    }
  }

  async function checkIn() {
    if (!selected) return;
    const updated = await localApi.checkInRegistration(token(), selected.id);
    setRegistrations((items) => items.map((item) => item.id === updated.data.registration.id ? updated.data.registration : item));
    setToast(`${updated.data.registration.registration_number} checked in`);
  }

  async function sendToBilling() {
    if (!selected) return;
    const response = await localApi.sendRegistrationToBilling(token(), selected.id);
    localStorage.setItem("counteros_billing_context", JSON.stringify(response.data.billing_context));
    router.push("/billing/new?from=registration");
  }

  useEffect(() => {
    void load("op", "");
  }, []);

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <div>
            <span className="chip">Hospital POS</span>
            <h1>Registration Center</h1>
          </div>
          <div className="actions screen-nav">
            <ScreenNavActions />
            <button type="button" onClick={() => void load()}>Refresh</button>
          </div>
        </div>

        <div className="status-grid">
          <Metric label="Today registrations" value={metrics.today} />
          <Metric label="OP queue" value={metrics.op} />
          <Metric label="IP admissions" value={metrics.ip} />
          <Metric label="Ready for billing" value={metrics.ready} />
          <Metric label="Pending billing" value={metrics.pending} />
        </div>

        <div className="tabs">
          {tabs.map((tab) => <button className={tab.type === activeType ? "active" : ""} key={tab.type} type="button" onClick={() => switchType(tab.type)}>{tab.label}</button>)}
        </div>

        <form className="form-grid" onSubmit={(event) => { event.preventDefault(); void load(activeType, query); }}>
          <label><span className="label">Search registrations</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Name, mobile, registration number" /></label>
          <div className="actions"><button type="submit">Search</button></div>
        </form>

        {toast ? <div className="toast">{toast}</div> : null}
        {state === "loading" ? <div className="status-grid" aria-label="Loading registrations"><div className="skeleton" /><div className="skeleton" /><div className="skeleton" /></div> : null}
        {state === "api-unavailable" ? <p className="error-text">API unavailable.</p> : null}
        {state === "permission-denied" ? <p className="error-text">Permission denied.</p> : null}
        {state === "error" ? <p className="error-text">{message}</p> : null}

        {state === "ready" ? (
          <div className="split-grid">
            <div>
              {registrations.length === 0 ? <p>No registrations found.</p> : null}
              <div className="status-grid">
                {registrations.map((item) => (
                  <button className="status-item" key={item.id} type="button" onClick={() => setSelectedId(item.id)}>
                    <span className="label">{item.registration_number} · {item.status}</span>
                    <span className="value">{item.patient_name}</span>
                    <p>{item.department_name ?? item.registration_type} {item.token_number ?? item.admission_number ?? ""}</p>
                    <span className="chip">{item.billing_status}</span>
                  </button>
                ))}
              </div>
            </div>
            <aside className="status-item">
              <span className="chip">Detail</span>
              <h2>{selected?.patient_name ?? "Select registration"}</h2>
              {selected ? (
                <>
                  <p>{selected.registration_number} · {selected.registration_type.toUpperCase()}</p>
                  <p>{selected.department_name ?? "No department"} {selected.doctor_name ? `· ${selected.doctor_name}` : ""}</p>
                  <p>{selected.ward ?? selected.token_number ?? selected.sample_status ?? selected.prescription_reference ?? selected.notes}</p>
                  <div className="actions">
                    <button type="button" onClick={() => void checkIn()}>Mark Checked In</button>
                    <button type="button" onClick={() => void sendToBilling()}>Send to Billing</button>
                  </div>
                </>
              ) : null}
            </aside>
          </div>
        ) : null}

        <form className="form-grid" onSubmit={create}>
          <h2>New Registration</h2>
          <div className="status-grid">
            <Field label={activeType === "pharmacy_walkin" ? "Patient/customer name" : "Patient name"} value={form.patient_name} onChange={(value) => setField("patient_name", value)} required={activeType !== "emergency"} />
            <Field label="Mobile number" value={form.mobile_number} onChange={(value) => setField("mobile_number", value)} />
            {["op", "ip", "follow_up"].includes(activeType) ? <Field label="Age" value={form.age_years} onChange={(value) => setField("age_years", value)} /> : null}
            {["op", "ip", "follow_up"].includes(activeType) ? <Select label="Gender" value={form.gender} onChange={(value) => setField("gender", value)} options={["", "male", "female", "other"]} /> : null}
            {["op", "ip", "emergency"].includes(activeType) ? <Select label="Department" value={form.department_id} onChange={(value) => setField("department_id", value)} options={["", ...departments.map((d) => d.id)]} labels={Object.fromEntries(departments.map((d) => [d.id, d.department_name]))} /> : null}
            {["op", "ip", "emergency"].includes(activeType) ? <Select label="Doctor" value={form.doctor_id} onChange={(value) => setField("doctor_id", value)} options={["", ...doctors.map((d) => d.id)]} labels={Object.fromEntries(doctors.map((d) => [d.id, d.full_name]))} /> : null}
            {activeType === "op" || activeType === "follow_up" ? <Select label="Visit type" value={form.visit_type} onChange={(value) => setField("visit_type", value)} options={["new", "follow_up"]} /> : null}
            {activeType === "ip" ? <Field label="Ward" value={form.ward} onChange={(value) => setField("ward", value)} /> : null}
            {activeType === "ip" ? <Field label="Room/bed" value={form.room_or_bed} onChange={(value) => setField("room_or_bed", value)} /> : null}
            {activeType === "ip" ? <Field label="Attender name" value={form.attender_name} onChange={(value) => setField("attender_name", value)} /> : null}
            {activeType === "ip" ? <Field label="Deposit amount" value={form.deposit_amount} onChange={(value) => setField("deposit_amount", value)} /> : null}
            {activeType === "emergency" ? <Select label="Priority" value={form.priority} onChange={(value) => setField("priority", value)} options={["high", "medium", "low"]} /> : null}
            {activeType === "lab" ? <Select label="Sample status" value={form.sample_status} onChange={(value) => setField("sample_status", value)} options={["sample_pending", "sample_collected"]} /> : null}
            {activeType === "pharmacy_walkin" ? <Field label="Prescription reference" value={form.prescription_reference} onChange={(value) => setField("prescription_reference", value)} /> : null}
          </div>
          <label><span className="label">Notes</span><textarea value={form.notes} onChange={(event) => setField("notes", event.target.value)} /></label>
          <div className="actions"><button disabled={saving} type="submit">{saving ? "Saving..." : "New Registration"}</button></div>
        </form>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="status-item"><span className="label">{label}</span><span className="value">{value}</span></div>;
}

function Field({ label, value, onChange, required = false }: { label: string; value: string; onChange: (value: string) => void; required?: boolean }) {
  return <label><span className="label">{label}</span><input required={required} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function Select({ label, value, onChange, options, labels = {} }: { label: string; value: string; onChange: (value: string) => void; options: string[]; labels?: Record<string, string> }) {
  return <label><span className="label">{label}</span><select value={value} onChange={(event) => onChange(event.target.value)}>{options.map((option) => <option key={option} value={option}>{labels[option] ?? (option || "Select")}</option>)}</select></label>;
}

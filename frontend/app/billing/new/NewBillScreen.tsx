"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { BillingContext, Department, Doctor, Patient, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function NewBillScreen() {
  const router = useRouter();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [patientId, setPatientId] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [doctorId, setDoctorId] = useState("");
  const [billingContext, setBillingContext] = useState<BillingContext | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "no-session" | "api-unavailable" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const authToken = token();
    const storedContext = localStorage.getItem("counteros_billing_context");
    const context = storedContext ? JSON.parse(storedContext) as BillingContext : null;
    setBillingContext(context);
    Promise.all([
      localApi.currentSession(authToken),
      localApi.patients(authToken),
      localApi.departments(authToken),
      localApi.doctors(authToken)
    ]).then(([session, patientList, departmentList, doctorList]) => {
      if (!session.data.session) {
        setState("no-session");
        return;
      }
      setPatients(patientList.data.items);
      setDepartments(departmentList.data.items);
      setDoctors(doctorList.data.items);
      setPatientId(context?.patient_id ?? patientList.data.items[0]?.id ?? "");
      setDepartmentId(context?.department_id ?? departmentList.data.items[0]?.id ?? "");
      setDoctorId(context?.doctor_id ?? doctorList.data.items[0]?.id ?? "");
      setState("ready");
    }).catch((error) => {
      const text = error instanceof Error ? error.message : "New bill load failed.";
      setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    });
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    try {
      let draftPatientId = patientId;
      if (!draftPatientId && billingContext?.patient_name) {
        const created = await localApi.createPatient(token(), { full_name: billingContext.patient_name, phone: billingContext.mobile_number ?? undefined });
        draftPatientId = created.data.patient.id;
      }
      const response = await localApi.createDraft(token(), {
        patient_id: draftPatientId || undefined,
        bill_type: billingContext?.registration_type === "ip" ? "ip" : "op",
        department_id: departmentId || undefined,
        doctor_id: doctorId || undefined,
        notes: billingContext ? `REGCTX:${JSON.stringify(billingContext)}\n${billingContext.notes}` : "OP visit"
      });
      localStorage.removeItem("counteros_billing_context");
      router.push(`/billing/drafts/${response.data.draft.id}`);
    } catch (error) {
      setState("error");
      setMessage(error instanceof Error ? error.message : "Draft create failed.");
    }
  }

  if (state === "loading") return <main><section className="shell panel"><h1>New Bill</h1><p>Loading.</p></section></main>;
  if (state === "no-session") return <main><section className="shell panel"><h1>New Bill</h1><p>Open cashier session before creating a bill.</p><Link className="button" href="/session/open">Open Session</Link></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>New Bill</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>New Bill</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header">
          <h1>New Bill</h1>
          <div className="actions screen-nav"><ScreenNavActions /></div>
        </div>
        {billingContext ? (
          <div className="toast">
            <strong>Billing from Registration</strong>
            <p>{label(billingContext.registration_type)} · {billingContext.registration_number} · {billingContext.patient_name}</p>
            {billingContext.token_number ? <p>Token {billingContext.token_number}</p> : null}
            {billingContext.admission_number ? <p>Admission {billingContext.admission_number} · {billingContext.ward ?? "Ward pending"} · {billingContext.room_or_bed ?? "Bed pending"}</p> : null}
            {billingContext.priority ? <p>Priority {billingContext.priority}</p> : null}
            {billingContext.deposit_amount ? <p>Deposit INR {billingContext.deposit_amount}</p> : null}
            <p>{billingContext.department_name ?? "Department pending"} {billingContext.doctor_name ? `· ${billingContext.doctor_name}` : ""}</p>
          </div>
        ) : null}
        <form className="form-grid" onSubmit={submit}>
          <label><span className="label">Patient</span><select value={patientId} onChange={(event) => setPatientId(event.target.value)}><option value="">{billingContext ? `Create patient: ${billingContext.patient_name}` : "Select patient"}</option>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name}</option>)}</select></label>
          <label><span className="label">Department</span><select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}>{departments.map((department) => <option key={department.id} value={department.id}>{department.department_name}</option>)}</select></label>
          <label><span className="label">Doctor</span><select value={doctorId} onChange={(event) => setDoctorId(event.target.value)}>{doctors.map((doctor) => <option key={doctor.id} value={doctor.id}>{doctor.full_name}</option>)}</select></label>
          <div className="actions"><button type="submit">Create Draft</button></div>
        </form>
      </section>
    </main>
  );
}

function label(type: string) {
  return type.split("_").map((part) => part[0].toUpperCase() + part.slice(1)).join(" ");
}

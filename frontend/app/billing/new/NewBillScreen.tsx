"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Department, Doctor, Patient, localApi } from "@/lib/api/client";

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
  const [state, setState] = useState<"loading" | "ready" | "no-session" | "api-unavailable" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const authToken = token();
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
      setPatientId(patientList.data.items[0]?.id ?? "");
      setDepartmentId(departmentList.data.items[0]?.id ?? "");
      setDoctorId(doctorList.data.items[0]?.id ?? "");
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
      const response = await localApi.createDraft(token(), {
        patient_id: patientId || undefined,
        bill_type: "op",
        department_id: departmentId || undefined,
        doctor_id: doctorId || undefined,
        notes: "OP visit"
      });
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
        <h1>New Bill</h1>
        <form className="form-grid" onSubmit={submit}>
          <label><span className="label">Patient</span><select value={patientId} onChange={(event) => setPatientId(event.target.value)}>{patients.map((patient) => <option key={patient.id} value={patient.id}>{patient.full_name}</option>)}</select></label>
          <label><span className="label">Department</span><select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}>{departments.map((department) => <option key={department.id} value={department.id}>{department.department_name}</option>)}</select></label>
          <label><span className="label">Doctor</span><select value={doctorId} onChange={(event) => setDoctorId(event.target.value)}>{doctors.map((doctor) => <option key={doctor.id} value={doctor.id}>{doctor.full_name}</option>)}</select></label>
          <div className="actions"><button type="submit">Create Draft</button></div>
        </form>
      </section>
    </main>
  );
}

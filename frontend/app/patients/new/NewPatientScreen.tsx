"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function NewPatientScreen() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [gender, setGender] = useState("");
  const [ageYears, setAgeYears] = useState("");
  const [address, setAddress] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      await localApi.createPatient(token(), {
        full_name: fullName,
        phone: phone || undefined,
        gender: gender || undefined,
        age_years: ageYears ? Number(ageYears) : undefined,
        address_line1: address || undefined
      });
      router.push("/patients");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Patient create failed.";
      setMessage(text.includes("PATIENT_FULL_NAME_REQUIRED") ? "Patient name required." : text);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="shell panel">
        <h1>New Patient</h1>
        <form onSubmit={submit} className="form-grid">
          <label><span className="label">Full name</span><input value={fullName} onChange={(event) => setFullName(event.target.value)} /></label>
          <label><span className="label">Phone</span><input value={phone} onChange={(event) => setPhone(event.target.value)} /></label>
          <label><span className="label">Gender</span><input value={gender} onChange={(event) => setGender(event.target.value)} /></label>
          <label><span className="label">Age years</span><input type="number" value={ageYears} onChange={(event) => setAgeYears(event.target.value)} /></label>
          <label><span className="label">Address</span><input value={address} onChange={(event) => setAddress(event.target.value)} /></label>
          {loading ? <p>Saving.</p> : null}
          {message ? <p className="error-text">{message}</p> : null}
          <div className="actions"><button type="submit">Create Patient</button></div>
        </form>
      </section>
    </main>
  );
}

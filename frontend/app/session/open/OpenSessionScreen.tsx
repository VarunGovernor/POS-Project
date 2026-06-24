"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { localApi } from "@/lib/api/client";

export function OpenSessionScreen() {
  const router = useRouter();
  const [counterName, setCounterName] = useState("OP Counter 1");
  const [amount, setAmount] = useState("1000");
  const [notes, setNotes] = useState("Morning shift");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    try {
      await localApi.openSession(localStorage.getItem("counteros_token"), {
        counter_name: counterName,
        opening_cash_amount: Number(amount),
        notes
      });
      sessionStorage.setItem("counteros_toast", "Session opened");
      router.push("/dashboard");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Open session failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <section className="shell panel">
        <h1>Open Session</h1>
        <form onSubmit={submit} className="form-grid">
          <label><span className="label">Counter</span><input value={counterName} onChange={(event) => setCounterName(event.target.value)} /></label>
          <label><span className="label">Opening cash</span><input type="number" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
          <label><span className="label">Notes</span><input value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          {loading ? <p>Opening session.</p> : null}
          {message ? <p className="error-text">{message}</p> : null}
          <div className="actions"><button type="submit">Open Session</button></div>
        </form>
      </section>
    </main>
  );
}

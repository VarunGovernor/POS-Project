"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { CashierSession, localApi } from "@/lib/api/client";

export function CloseSessionScreen() {
  const router = useRouter();
  const [session, setSession] = useState<CashierSession | null>(null);
  const [amount, setAmount] = useState("1000");
  const [notes, setNotes] = useState("Shift closed");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    localApi.currentSession(localStorage.getItem("counteros_token"))
      .then((response) => setSession(response.data.session))
      .catch((error) => setMessage(error instanceof Error ? error.message : "Session load failed."))
      .finally(() => setLoading(false));
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    setLoading(true);
    setMessage("");
    try {
      await localApi.closeSession(localStorage.getItem("counteros_token"), {
        session_id: session.id,
        closing_cash_amount: Number(amount),
        notes
      });
      router.push("/dashboard");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Close session failed.");
    } finally {
      setLoading(false);
    }
  }

  if (loading) return <main><section className="shell panel"><h1>Close Session</h1><p>Loading.</p></section></main>;
  if (!session) return <main><section className="shell panel"><h1>Close Session</h1><p>No open cashier session.</p>{message ? <p className="error-text">{message}</p> : null}</section></main>;

  return (
    <main>
      <section className="shell panel">
        <h1>Close Session</h1>
        <form onSubmit={submit} className="form-grid">
          <p>Session {session.session_number}</p>
          <label><span className="label">Closing cash</span><input type="number" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
          <label><span className="label">Notes</span><input value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          {message ? <p className="error-text">{message}</p> : null}
          <div className="actions"><button type="submit">Close Session</button></div>
        </form>
      </section>
    </main>
  );
}

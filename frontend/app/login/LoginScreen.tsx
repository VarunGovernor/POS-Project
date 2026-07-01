"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

import { localApi } from "@/lib/api/client";

type Pos = "hospital" | "liquor";

const posLabels: Record<Pos, string> = {
  hospital: "Hospital POS",
  liquor: "Liquor Store POS"
};

export function LoginScreen({ selectedPos }: { selectedPos?: string }) {
  const router = useRouter();
  const pos = selectedPos === "hospital" || selectedPos === "liquor" ? selectedPos : null;
  const [username, setUsername] = useState("cashier");
  const [password, setPassword] = useState("");
  const [counterName, setCounterName] = useState(pos === "liquor" ? "Liquor Counter 1" : "OP Counter 1");
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "api-unavailable">("idle");
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!pos) return;
    setStatus("loading");
    setMessage("");
    if (pos === "liquor") {
      localStorage.setItem("liquor_pos_cashier", username);
      setStatus("idle");
      router.push("/liquor/dashboard");
      return;
    }
    try {
      const response = await localApi.login({ username, password, counter_name: counterName });
      localStorage.setItem("counteros_token", response.data.session_token);
      setStatus("idle");
      router.push("/dashboard");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Login failed.";
      if (text.toLowerCase().includes("fetch")) {
        setStatus("api-unavailable");
        setMessage("Local API unavailable.");
        return;
      }
      setStatus("error");
      setMessage(text.includes("AUTH_INVALID_CREDENTIALS") ? "Invalid username or password." : text);
    }
  }

  if (!pos) {
    return (
      <main>
        <section className="shell panel">
          <span className="chip">HamTech POS OS</span>
          <h1>Select a POS system before login.</h1>
          <div className="actions">
            <button type="button" onClick={() => router.push("/")}>Select POS System</button>
          </div>
        </section>
      </main>
    );
  }

  return (
    <main>
      <section className="shell panel">
        <span className="chip">HamTech POS OS</span>
        <h1>{posLabels[pos]} Login</h1>
        <form onSubmit={submit} className="form-grid">
          <label>
            <span className="label">Username</span>
            <input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label>
            <span className="label">Password</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          <label>
            <span className="label">Counter</span>
            <input value={counterName} onChange={(event) => setCounterName(event.target.value)} />
          </label>
          {status === "loading" ? <p>Logging in.</p> : null}
          {message ? <p className="error-text">{message}</p> : null}
          <div className="actions">
            <button type="submit">Login</button>
            <button className="secondary" type="button" onClick={() => router.push("/")}>Select POS System</button>
          </div>
        </form>
      </section>
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";

import { PrinterJob, PrinterStatus, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function PrinterScreen() {
  const [status, setStatus] = useState<PrinterStatus | null>(null);
  const [jobs, setJobs] = useState<PrinterJob[]>([]);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "error">("loading");

  async function load() {
    setState("loading");
    setMessage("");
    try {
      const [statusResponse, jobsResponse] = await Promise.all([
        localApi.printerStatus(token()),
        localApi.printerJobs(token())
      ]);
      setStatus(statusResponse.data);
      setJobs(jobsResponse.data.items);
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Printer load failed.";
      setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  async function testPrint() {
    try {
      await localApi.printerTest(token());
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Test print failed.");
    }
  }

  async function retry(jobId: string) {
    try {
      await localApi.retryPrinterJob(token(), jobId);
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Retry failed.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") return <main><section className="shell panel"><h1>Printer</h1><p>Loading.</p></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Printer</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>Printer</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Printer</h1><span className="value">{status?.status}</span></div>
        {message ? <p className="error-text">{message}</p> : null}
        {status?.status === "not_configured" ? <p className="error-text">Printer not configured.</p> : null}
        {status?.printer ? <p>{status.printer.printer_name} · {status.printer.printer_type}</p> : null}
        <div className="actions"><button type="button" onClick={testPrint}>Test Print</button><button type="button" onClick={load}>Refresh</button></div>
        {jobs.length === 0 ? <p>No printer jobs.</p> : null}
        <div className="status-grid">
          {jobs.map((job) => (
            <div className="status-item" key={job.id}>
              <span className="label">{job.job_number}</span>
              <span className="value">{job.status}</span>
              <p>{job.job_type} · attempts {job.attempt_count}</p>
              {job.failure_message ? <p className="error-text">{job.failure_message}</p> : null}
              {job.status === "failed" ? <button type="button" onClick={() => retry(job.id)}>Retry</button> : null}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

"use client";

import { useRouter } from "next/navigation";

import { localApi } from "@/lib/api/client";

export function SupportRequiredScreen({ reason }: { reason: string }) {
  const router = useRouter();

  async function retryCheck() {
    await localApi.startupStatus();
    router.push("/startup");
  }

  return (
    <main>
      <section className="shell panel">
        <h1>Support required</h1>
        <p className="error-text">{reason}</p>
        <div className="actions">
          <button type="button" onClick={retryCheck}>
            Retry check
          </button>
        </div>
      </section>
    </main>
  );
}

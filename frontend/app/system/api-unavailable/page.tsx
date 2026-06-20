"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { localApi } from "@/lib/api/client";

export default function ApiUnavailablePage() {
  const router = useRouter();

  async function retry() {
    await localApi.health();
    router.push("/startup");
  }

  return (
    <main>
      <section className="shell panel">
        <h1>Local API unavailable</h1>
        <p>Local backend API did not respond.</p>
        <div className="actions">
          <button type="button" onClick={retry}>
            Retry
          </button>
          <Link className="button secondary" href="/system/support-required">
            Open Support
          </Link>
        </div>
      </section>
    </main>
  );
}

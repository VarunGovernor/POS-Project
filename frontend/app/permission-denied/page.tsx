"use client";

import { useRouter } from "next/navigation";

export default function PermissionDeniedPage() {
  const router = useRouter();

  return (
    <main>
      <section className="shell panel">
        <h1>Permission denied</h1>
        <p>Current user cannot access requested screen.</p>
        <div className="actions">
          <button type="button" onClick={() => router.back()}>
            Back
          </button>
        </div>
      </section>
    </main>
  );
}

"use client";

import { useRouter } from "next/navigation";

export function ScreenNavActions() {
  const router = useRouter();

  function back() {
    if (typeof window !== "undefined" && window.history.length > 1) router.back();
    else router.push("/dashboard");
  }

  return (
    <>
      <button className="secondary" type="button" onClick={back}>← Back</button>
      <button className="secondary" type="button" onClick={() => router.push("/dashboard")}>Dashboard</button>
    </>
  );
}

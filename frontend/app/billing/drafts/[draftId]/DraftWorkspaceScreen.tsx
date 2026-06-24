"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { LoadingPanel } from "@/app/components/LoadingPanel";
import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { BillDraft, ServiceItem, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function DraftWorkspaceScreen({ draftId }: { draftId: string }) {
  const router = useRouter();
  const [draft, setDraft] = useState<BillDraft | null>(null);
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [cashReceived, setCashReceived] = useState("");
  const [message, setMessage] = useState("");
  const [toast, setToast] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "not-found" | "api-unavailable" | "error">("loading");

  async function load() {
    setState("loading");
    try {
      const [draftResponse, serviceResponse] = await Promise.all([
        localApi.draft(token(), draftId),
        localApi.services(token())
      ]);
      setDraft(draftResponse.data.draft);
      setServices(serviceResponse.data.items);
      setServiceId(serviceResponse.data.items[0]?.id ?? "");
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Draft load failed.";
      if (text.includes("BILL_DRAFT_NOT_FOUND")) setState("not-found");
      else setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  async function addItem() {
    await localApi.addDraftItem(token(), draftId, { service_id: serviceId, quantity: 1, discount_amount: 0 });
    await load();
  }

  async function editItem(itemId: string, quantity: number, discount_amount: number) {
    await localApi.updateDraftItem(token(), draftId, itemId, { quantity, discount_amount });
    await load();
  }

  async function removeItem(itemId: string) {
    await localApi.removeDraftItem(token(), draftId, itemId);
    await load();
  }

  async function voidDraft() {
    await localApi.voidDraft(token(), draftId, "Patient cancelled visit");
    await load();
  }

  async function finalizeDraft() {
    if (!draft) return;
    setMessage("");
    const key = globalThis.crypto?.randomUUID?.() ?? `IDEM-${Date.now()}`;
    try {
      const response = await localApi.finalizeDraft(token(), draftId, key, {
        payment_method: "cash",
        received_amount: Number(cashReceived || draft.total_amount || 0),
        notes: "Cash received"
      });
      sessionStorage.setItem("counteros_toast", "Bill finalized");
      router.push(`/billing/bills/${response.data.bill.id}`);
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Finalize failed.");
    }
  }

  useEffect(() => {
    const pendingToast = sessionStorage.getItem("counteros_toast");
    sessionStorage.removeItem("counteros_toast");
    setToast(pendingToast ?? "");
    void load();
  }, [draftId]);

  if (state === "loading") return <LoadingPanel title="Draft" />;
  if (state === "not-found") return <main><section className="shell panel"><h1>Draft not found</h1></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Draft</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "error" || !draft) return <main><section className="shell panel"><h1>Draft</h1><p className="error-text">{message}</p></section></main>;

  const items = draft.items ?? [];
  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Draft {draft.draft_number}</h1><div className="actions screen-nav"><ScreenNavActions /><span className="value">{draft.status}</span></div></div>
        {toast ? <div className="toast">{toast}</div> : null}
        {draft.status === "voided" ? <p className="error-text">Draft voided.</p> : null}
        {message ? <p className="error-text">{message}</p> : null}
        <p>Autosaved {draft.last_autosaved_at}</p>
        {draft.status === "draft" ? (
          <div className="actions">
            <select aria-label="Service" value={serviceId} onChange={(event) => setServiceId(event.target.value)}>{services.map((service) => <option key={service.id} value={service.id}>{service.service_name}</option>)}</select>
            <button type="button" onClick={addItem}>Add Item</button>
            <button type="button" onClick={voidDraft}>Void Draft</button>
          </div>
        ) : null}
        {items.length === 0 ? <p>No draft items.</p> : null}
        <div className="status-grid">
          {items.map((item) => (
            <div className="status-item" key={item.id}>
              <span className="label">{item.service_name_at_time}</span>
              <span className="value">{item.final_line_total}</span>
              <p>Qty {item.quantity}, discount {item.discount_amount}</p>
              {draft.status === "draft" ? (
                <div className="actions">
                  <button type="button" onClick={() => editItem(item.id, item.quantity + 1, item.discount_amount)}>+ Qty</button>
                  <button type="button" onClick={() => removeItem(item.id)}>Remove</button>
                </div>
              ) : null}
            </div>
          ))}
        </div>
        <div className="status-grid">
          <div className="status-item"><span className="label">Subtotal</span><span className="value">{draft.subtotal_amount}</span></div>
          <div className="status-item"><span className="label">Discount</span><span className="value">{draft.discount_amount}</span></div>
          <div className="status-item"><span className="label">Tax</span><span className="value">{draft.tax_amount}</span></div>
          <div className="status-item"><span className="label">Total</span><span className="value">{draft.total_amount}</span></div>
        </div>
        {draft.status === "draft" ? (
          <div className="form-grid">
            <span className="label">Payment method</span>
            <span className="value">Cash</span>
            <label><span className="label">Cash received</span><input type="number" value={cashReceived} onChange={(event) => setCashReceived(event.target.value)} /></label>
            <div className="actions"><button type="button" onClick={finalizeDraft}>Finalize Bill</button></div>
          </div>
        ) : null}
      </section>
    </main>
  );
}

"use client";

import { useMemo, useState } from "react";

type Stage = "landing" | "select" | "dashboard";
type ModuleKey = "close" | "lookup" | "catalog" | "new" | "drafts" | "bills" | "printer" | "recovery" | "sync" | "reports" | "settings" | "support" | "audit";

type Vertical = {
  name: string;
  desc: string;
  modules: string;
  lookup: string;
  catalog: string;
  newBill: string;
  draft: string;
  final: string;
  receiptSubject: string;
  items: string[];
  metrics: string[];
};

const verticals: Vertical[] = [
  { name: "Hospital POS", desc: "OP billing, patient services, receipt workflow.", modules: "OP Billing, Patients, Services, Recovery", lookup: "Patient Lookup", catalog: "Catalog / Services", newBill: "OP Billing", draft: "Draft Bills", final: "Final Bills", receiptSubject: "Acceptance Patient", items: ["OP Consultation", "General Medicine", "Dr. Sharma"], metrics: ["OP Billing", "Patient Lookup", "Draft Bills"] },
  { name: "Restaurant POS", desc: "Tables, orders, kitchen token, cash billing.", modules: "Tables, Orders, Menu, Kitchen", lookup: "Table Lookup", catalog: "Menu Lookup", newBill: "New Order", draft: "Draft Orders", final: "Final Bills", receiptSubject: "Table 08", items: ["Masala Dosa", "Filter Coffee", "Kitchen Token"], metrics: ["Tables", "Orders", "Kitchen Token"] },
  { name: "Gas Station POS", desc: "Pump sales, shift sessions, fuel receipts.", modules: "Pumps, Fuel, Shift, Bills", lookup: "Pump Lookup", catalog: "Fuel Products", newBill: "New Sale", draft: "Draft Sales", final: "Final Bills", receiptSubject: "Pump 03", items: ["Petrol", "18.5 liters", "Nozzle A"], metrics: ["Pump Sales", "Fuel Products", "Shift Session"] },
  { name: "Retail POS", desc: "Counter sales, cart, products, receipts.", modules: "Products, Cart, Bills, Printer", lookup: "Customer Lookup", catalog: "Product Lookup", newBill: "New Sale", draft: "Draft Sales", final: "Final Bills", receiptSubject: "Walk-in Customer", items: ["Cotton Shirt", "Notebook", "Carry Bag"], metrics: ["Product Lookup", "Cart", "Draft Sales"] },
  { name: "Pharmacy POS", desc: "Medicine billing with prescription references.", modules: "Medicines, Batch, Billing", lookup: "Prescription Reference", catalog: "Medicine Lookup", newBill: "New Bill", draft: "Draft Bills", final: "Final Bills", receiptSubject: "Prescription RX-1042", items: ["Paracetamol 500", "Batch B24", "Expiry 2027"], metrics: ["Medicine Lookup", "Batch/Expiry Demo", "Draft Bills"] },
  { name: "Laboratory POS", desc: "Test billing, patient lookup, sample receipts.", modules: "Tests, Samples, Bills", lookup: "Patient Lookup", catalog: "Test Lookup", newBill: "Sample Billing", draft: "Draft Bills", final: "Final Bills", receiptSubject: "Lab Patient", items: ["CBC", "Thyroid Profile", "Sample ID S-91"], metrics: ["Test Lookup", "Sample Billing", "Reports"] },
  { name: "Parking POS", desc: "Vehicle entry, duration pricing, ticket billing.", modules: "Vehicles, Tickets, Duration", lookup: "Vehicle Entry", catalog: "Duration Pricing", newBill: "Ticket Billing", draft: "Draft Tickets", final: "Final Bills", receiptSubject: "TS09 AB 1234", items: ["Vehicle Entry", "2 hours", "Exit Gate 1"], metrics: ["Vehicle Entry", "Ticket Billing", "Duration Pricing"] },
  { name: "Ticketing POS", desc: "Ticket counter, pass lookup, receipt billing.", modules: "Tickets, Passes, Receipts", lookup: "Seat/Pass Lookup", catalog: "Ticket Counter", newBill: "New Ticket", draft: "Draft Tickets", final: "Final Bills", receiptSubject: "Pass P-2201", items: ["Entry Ticket", "Seat A12", "Counter 2"], metrics: ["Ticket Counter", "Seat/Pass Lookup", "Final Bills"] },
  { name: "School / College Fee Counter", desc: "Student lookup, fee heads, receipts.", modules: "Students, Fees, Receipts", lookup: "Student Lookup", catalog: "Fee Heads", newBill: "Draft Fee Receipt", draft: "Draft Fee Receipt", final: "Final Receipts", receiptSubject: "Student ST-120", items: ["Tuition Fee", "Library Fee", "Term 1"], metrics: ["Student Lookup", "Fee Heads", "Final Receipts"] },
  { name: "Service Billing POS", desc: "Customer services, invoices, cash receipts.", modules: "Customers, Services, Invoices", lookup: "Customer Lookup", catalog: "Service Catalog", newBill: "Draft Invoice", draft: "Draft Invoice", final: "Final Bills", receiptSubject: "Customer C-88", items: ["Installation", "Service Visit", "Warranty Check"], metrics: ["Customer Lookup", "Service Catalog", "Draft Invoice"] }
];

const modules: Array<{ key: ModuleKey; common: string }> = [
  { key: "close", common: "Close Session" },
  { key: "lookup", common: "Lookup" },
  { key: "catalog", common: "Catalog" },
  { key: "new", common: "New Bill" },
  { key: "drafts", common: "Drafts" },
  { key: "bills", common: "Bills" },
  { key: "printer", common: "Printer" },
  { key: "recovery", common: "Recovery" },
  { key: "sync", common: "Sync" },
  { key: "reports", common: "Reports" },
  { key: "settings", common: "Settings" },
  { key: "support", common: "Support" },
  { key: "audit", common: "Audit" }
];

function moduleName(v: Vertical, key: ModuleKey) {
  if (key === "lookup") return v.lookup;
  if (key === "catalog") return v.catalog;
  if (key === "new") return v.newBill;
  if (key === "drafts") return v.draft;
  if (key === "bills") return v.final;
  return modules.find((item) => item.key === key)?.common ?? key;
}

export default function DemoPage() {
  const [stage, setStage] = useState<Stage>("landing");
  const [vertical, setVertical] = useState<Vertical>(verticals[0]);
  const [active, setActive] = useState<ModuleKey>("new");
  const [toast, setToast] = useState("Ready");
  const [qty, setQty] = useState(1);
  const [finalized, setFinalized] = useState(false);
  const [syncDone, setSyncDone] = useState(false);
  const [printJobs, setPrintJobs] = useState<string[]>(["Queue clear"]);
  const [closed, setClosed] = useState(false);
  const total = qty * 500;
  const billNumber = useMemo(() => `HT-${vertical.name.split(" ")[0].toUpperCase()}-20260620-0001`, [vertical]);

  function notify(text: string) {
    setToast(text);
  }

  function choose(next: Vertical) {
    if (next.name !== "Hospital POS") {
      notify("This POS vertical is planned for a future rollout.");
      return;
    }
    setVertical(next);
    setActive("new");
    setStage("dashboard");
    setQty(1);
    setFinalized(false);
    setSyncDone(false);
    setClosed(false);
    setPrintJobs(["Queue clear"]);
    notify(`${next.name} loaded`);
  }

  return (
    <main className="demo-page">
      <div className="demo-shell">
        <div className="toast" role="status">{toast}</div>

        {stage === "landing" ? (
          <section className="hero screen">
            <div className="brand">HamTech Innovations</div>
            <h1>HamTech POS OS</h1>
            <p className="lead">Offline-first multi-industry billing appliance platform.</p>
            <p>One POS operating layer for hospitals, restaurants, gas stations, retail counters, pharmacies, labs, parking, ticketing, and service billing.</p>
            <button className="primary" onClick={() => { setStage("select"); notify("Select a POS system"); }}>Start Demo</button>
          </section>
        ) : null}

        {stage === "select" ? (
          <section className="screen">
            <div className="topbar"><div><span className="brand">HamTech Innovations</span><h1>Select POS System</h1></div><button onClick={() => setStage("landing")}>Back</button></div>
            <div className="vertical-grid">
              {verticals.map((item) => (
                <button className={item.name === "Hospital POS" ? "vertical-card" : "vertical-card future"} key={item.name} onClick={() => choose(item)}>
                  <span className="badge">{item.name === "Hospital POS" ? "Ready" : "Coming Soon"}</span>
                  <h2>{item.name}</h2>
                  <p>{item.desc}</p>
                  <small>{item.modules}</small>
                </button>
              ))}
            </div>
          </section>
        ) : null}

        {stage === "dashboard" ? (
          <section className="screen dashboard">
            <aside className="rail">
              <button className="logo" onClick={() => setStage("select")}>HamTech POS OS</button>
              <p>{vertical.name}</p>
              {modules.map((item) => (
                <button className={active === item.key ? "nav active" : "nav"} key={item.key} onClick={() => { setActive(item.key); notify(`${moduleName(vertical, item.key)} opened`); }}>
                  {moduleName(vertical, item.key)}
                </button>
              ))}
              <button className="nav" onClick={() => { setStage("select"); notify("Logged out"); }}>Logout</button>
            </aside>
            <div className="work">
              <div className="topbar">
                <div><span className="brand">HamTech Innovations</span><h1>{vertical.name}</h1></div>
                <div className="chips"><span>Offline-first</span><span>Device active</span><span>Local Printer</span></div>
              </div>
              <div className="metric-row">
                {vertical.metrics.map((metric, index) => <div className="metric" key={metric}><small>{metric}</small><strong>{index === 0 ? "Ready" : index === 1 ? "Active" : "Synced"}</strong></div>)}
              </div>
              <Panel vertical={vertical} active={active} qty={qty} setQty={setQty} total={total} finalized={finalized} setFinalized={setFinalized} syncDone={syncDone} setSyncDone={setSyncDone} printJobs={printJobs} setPrintJobs={setPrintJobs} closed={closed} setClosed={setClosed} billNumber={billNumber} notify={notify} />
            </div>
          </section>
        ) : null}
      </div>
      <style>{styles}</style>
    </main>
  );
}

function Panel(props: {
  vertical: Vertical; active: ModuleKey; qty: number; setQty: (n: number) => void; total: number; finalized: boolean; setFinalized: (v: boolean) => void;
  syncDone: boolean; setSyncDone: (v: boolean) => void; printJobs: string[]; setPrintJobs: (v: string[]) => void; closed: boolean; setClosed: (v: boolean) => void; billNumber: string; notify: (s: string) => void;
}) {
  const v = props.vertical;
  if (props.active === "new") return <Card title={v.newBill}><div className="split"><div><p>Selected account: <b>{v.receiptSubject}</b></p><p>Service/item: <b>{v.items[0]}</b></p><div className="stepper"><button onClick={() => { props.setQty(Math.max(1, props.qty - 1)); props.notify("Quantity updated"); }}>-</button><strong>{props.qty}</strong><button onClick={() => { props.setQty(props.qty + 1); props.notify("Quantity updated"); }}>+</button></div><button className="primary" onClick={() => { props.setFinalized(true); props.notify(`Bill finalized: ${props.billNumber}`); }}>Finalize Bill</button></div><Receipt v={v} total={props.total} billNumber={props.billNumber} finalized={props.finalized} /></div></Card>;
  if (props.active === "drafts") return <Card title={v.draft}><Rows rows={[["DRAFT-001", `${v.receiptSubject} · autosaved now`, "Continue"], ["DRAFT-002", `${v.items[0]} · autosaved 4 min ago`, "Void draft"]]} /><button onClick={() => props.notify("Draft autosaved")}>Autosave Draft</button></Card>;
  if (props.active === "bills") return <Card title={v.final}><Rows rows={[[props.billNumber, `Paid cash · receipt generated · ${props.total}`, "View detail"], ["HT-ARCHIVE-0007", "Synced · printed", "Open receipt"]]} /></Card>;
  if (props.active === "printer") return <Card title="Receipt Printer"><div className="metric-row"><div className="metric"><small>Status</small><strong>Local Printer Active</strong></div><div className="metric"><small>Jobs</small><strong>{props.printJobs.length}</strong></div></div><button onClick={() => { props.setPrintJobs(["Test receipt printed", ...props.printJobs]); props.notify("Receipt printed"); }}>Print Test Receipt</button><button onClick={() => { props.setPrintJobs(["Duplicate copy printed", ...props.printJobs]); props.notify("Receipt reprinted"); }}>Reprint Receipt</button><Rows rows={props.printJobs.map((job, i) => [`JOB-${i + 1}`, job, "printed"])} /></Card>;
  if (props.active === "sync") return <Card title="Sync"><div className="metric-row"><div className="metric"><small>Adapter</small><strong>Offline Sync Queue</strong></div><div className="metric"><small>Status</small><strong>{props.syncDone ? "Synced" : "Pending"}</strong></div></div><button className="primary" onClick={() => { props.setSyncDone(true); props.notify("Sync completed using offline sync queue"); }}>Retry Sync</button><Rows rows={[[props.syncDone ? "SYNCED" : "PENDING", "BILL_FINALIZED", props.syncDone ? "attempt recorded" : "waiting"]]} /></Card>;
  if (props.active === "recovery") return <Card title="Recovery"><Rows rows={[["Open draft found", "Review available draft", "acknowledge"], ["Pending print job found", "Print queue needs review", "acknowledge"], ["Unsynced bill found", "Outbox event pending", "acknowledge"]]} /><button onClick={() => props.notify("Recovery scan completed")}>Run Recovery Scan</button></Card>;
  if (props.active === "reports") return <Card title="Reports"><div className="metric-row"><div className="metric"><small>Today collection</small><strong>{props.total}</strong></div><div className="metric"><small>Bill count</small><strong>{props.finalized ? 1 : 0}</strong></div><div className="metric"><small>Cash collected</small><strong>{props.finalized ? props.total : 0}</strong></div></div><Rows rows={[[v.items[0], "Category sales", String(props.total)], [v.items[1], "Secondary line", "320"]]} /></Card>;
  if (props.active === "settings") return <Card title="Settings"><Rows rows={[["Receipt header", "HamTech POS OS", "editable"], ["Counter name", "Counter 01", "saved"], ["Device mode", "Appliance demo", "readonly"]]} /><button onClick={() => props.notify("Setting saved")}>Update Setting</button></Card>;
  if (props.active === "support") return <Card title="Support"><div className="metric-row"><div className="metric"><small>API</small><strong>ok</strong></div><div className="metric"><small>Database</small><strong>ok</strong></div><div className="metric"><small>Printer</small><strong>active</strong></div><div className="metric"><small>Sync</small><strong>{props.syncDone ? "ok" : "pending"}</strong></div></div><button onClick={() => props.notify("Support bundle created: SUP-DEMO-001")}>Create Support Bundle</button></Card>;
  if (props.active === "audit") return <Card title="Audit"><Rows rows={[["Login", "Cashier authenticated", "now"], ["Session opened", "Counter 01", "now"], ["Bill finalized", props.billNumber, props.finalized ? "done" : "ready"], ["Receipt printed", "Local Printer", props.printJobs.length > 1 ? "done" : "waiting"], ["Sync retried", "Offline Sync Queue", props.syncDone ? "done" : "waiting"], ["Support bundle created", "SUP-DEMO-001", "ready"]]} /></Card>;
  if (props.active === "close") return <Card title="Close Session"><div className="metric-row"><div className="metric"><small>Opening cash</small><strong>1000</strong></div><div className="metric"><small>Collected cash</small><strong>{props.finalized ? props.total : 0}</strong></div><div className="metric"><small>Expected cash</small><strong>{1000 + (props.finalized ? props.total : 0)}</strong></div></div><button className="primary" onClick={() => { props.setClosed(true); props.notify("Session closed"); }}>Close Session</button>{props.closed ? <p className="success">Session closed successfully.</p> : null}</Card>;
  if (props.active === "lookup") return <Card title={v.lookup}><Rows rows={[[v.receiptSubject, "Active profile", "select"], ["Recent account", "Last visit today", "open"]]} /><button onClick={() => props.notify(`${v.lookup} selected`)}>Select Record</button></Card>;
  return <Card title={v.catalog}><Rows rows={v.items.map((item, i) => [item, i === 0 ? "Primary item" : "Available", `₹${(i + 1) * 250}`])} /><button onClick={() => props.notify("Catalog item added")}>Add Item</button></Card>;
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return <div className="panel-card"><h2>{title}</h2>{children}</div>;
}

function Rows({ rows }: { rows: string[][] }) {
  return <div className="rows">{rows.map((row) => <div className="row" key={row.join("-")}>{row.map((cell) => <span key={cell}>{cell}</span>)}</div>)}</div>;
}

function Receipt({ v, total, billNumber, finalized }: { v: Vertical; total: number; billNumber: string; finalized: boolean }) {
  return <div className="receipt"><small>Receipt Preview</small><h3>{billNumber}</h3><p>{v.receiptSubject}</p><p>{v.items.join(" · ")}</p><div className="line"><span>Cash paid</span><b>{total}</b></div><div className="line"><span>Change</span><b>0</b></div><strong>{finalized ? "Receipt generated" : "Ready to finalize"}</strong></div>;
}

const styles = `
.demo-page{min-height:100vh;background:linear-gradient(135deg,#f8fbff,#eef4f1 45%,#fff7ed);color:#13222f;font-family:Inter,Arial,sans-serif;padding:28px}.demo-shell{max-width:1240px;margin:0 auto}.screen{animation:rise .35s ease both}.hero{min-height:calc(100vh - 56px);display:grid;align-content:center;gap:18px;max-width:820px}.brand{color:#176b87;font-weight:800;letter-spacing:.08em;text-transform:uppercase;font-size:12px}.hero h1,.topbar h1{font-size:clamp(38px,7vw,76px);line-height:1;margin:0}.lead{font-size:24px;color:#1c3445}.hero p{font-size:18px;max-width:760px}.primary,button{border:0;border-radius:14px;background:#12384b;color:#fff;min-height:44px;padding:0 18px;font-weight:800;cursor:pointer;box-shadow:0 14px 30px #12384b24;transition:.2s}button:hover{transform:translateY(-1px);box-shadow:0 18px 34px #12384b30}.topbar{display:flex;justify-content:space-between;align-items:center;gap:18px;margin-bottom:22px}.vertical-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px}.vertical-card,.panel-card,.metric,.receipt{background:rgba(255,255,255,.72);border:1px solid rgba(255,255,255,.8);box-shadow:0 20px 60px rgba(37,63,88,.12);backdrop-filter:blur(16px)}.vertical-card{text-align:left;color:#13222f;border-radius:22px;padding:20px;min-height:190px}.vertical-card.future{opacity:.72}.vertical-card.future .badge{background:#eef4f6;color:#49616f}.vertical-card h2{margin:18px 0 8px}.vertical-card p,.vertical-card small{color:#586776}.badge,.chips span{display:inline-flex;border-radius:999px;background:#e6f6ef;color:#116644;padding:6px 10px;font-size:12px;font-weight:800}.dashboard{display:grid;grid-template-columns:260px 1fr;gap:18px}.rail{background:#102f40;color:#fff;border-radius:26px;padding:18px;min-height:calc(100vh - 56px);position:sticky;top:28px}.rail p{color:#b8d4df}.logo,.nav{width:100%;justify-content:flex-start;margin-bottom:8px;background:transparent;box-shadow:none;color:#fff}.nav.active,.nav:hover{background:rgba(255,255,255,.14)}.work{min-width:0}.chips{display:flex;flex-wrap:wrap;gap:8px}.metric-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:16px}.metric{border-radius:18px;padding:16px}.metric small,.receipt small{display:block;color:#667787;margin-bottom:8px}.metric strong{font-size:22px}.panel-card{border-radius:28px;padding:24px}.split{display:grid;grid-template-columns:minmax(0,1fr) 320px;gap:18px}.stepper{display:flex;align-items:center;gap:12px;margin:16px 0}.stepper button{min-width:44px;padding:0}.receipt{border-radius:20px;padding:18px;background:#fff}.receipt h3{margin:8px 0}.line{display:flex;justify-content:space-between;border-top:1px dashed #cbd5df;padding-top:10px;margin-top:10px}.rows{display:grid;gap:10px;margin:16px 0}.row{display:grid;grid-template-columns:1fr 1.4fr auto;gap:10px;align-items:center;padding:12px;border:1px solid #e2e8f0;border-radius:14px;background:#fff}.toast{position:fixed;right:24px;top:20px;z-index:10;background:#102f40;color:#fff;border-radius:999px;padding:10px 16px;box-shadow:0 16px 34px #102f4030}.success{color:#116644;font-weight:800}@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}@media(max-width:860px){.dashboard,.split{grid-template-columns:1fr}.rail{position:relative;top:0;min-height:auto}.topbar{align-items:flex-start;flex-direction:column}.demo-page{padding:16px}.row{grid-template-columns:1fr}}`;

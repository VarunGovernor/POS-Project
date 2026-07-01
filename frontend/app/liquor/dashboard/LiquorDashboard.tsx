"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const modules = ["Age Verification", "Customer / Counter Sale", "Product Lookup", "Stock Check", "New Sale", "Draft Sales", "Bills / Receipts", "Printer", "Sync", "Recovery", "Reports", "Settings", "Support", "Audit", "Close Session", "Logout"];
const categories = ["All", "Beer", "Wine", "Whisky", "Vodka", "Rum", "Gin", "Brandy", "Ready-to-drink", "Mixers / Non-alcoholic add-ons"];

type Product = { sku: string; name: string; category: string; size: string; price: number; tax: number; stockCount: number; minimumStock: number; ageRestricted: boolean; batch: string };
type CartItem = Product & { qty: number };
type Customer = { id: string; name: string; type: string; account: string; lastVisit: string };
type Receipt = { number: string; customer: string; amount: number; payment: string; age: string; print: string; sync: string; time: string; items: CartItem[] };
type Draft = { number: string; customer: string; items: CartItem[]; amount: number; autosaved: string; status: string };
type Job = { id: string; receipt: string; status: string; device: string; time: string };
type Event = { id: string; detail: string; status: string; time: string };
type Marker = { id: string; type: string; detail: string; status: string };
type Settings = { store: string; counter: string; header: string; footer: string; taxDisplay: string; printer: string; sync: string };
type DashboardApi = {
  active: string; setActive: (value: string) => void; inventory: Product[]; setInventory: (value: Product[]) => void;
  selectedCustomer: Customer; setSelectedCustomer: (value: Customer) => void; saleType: string; setSaleType: (value: string) => void;
  ageStatus: string; setAgeStatus: (value: string) => void; dob: string; setDob: (value: string) => void;
  cart: CartItem[]; setCart: (value: CartItem[]) => void; payment: string; setPayment: (value: string) => void;
  drafts: Draft[]; setDrafts: (value: Draft[]) => void; receipts: Receipt[]; setReceipts: (value: Receipt[]) => void;
  printerJobs: Job[]; setPrinterJobs: (value: Job[]) => void; syncEvents: Event[]; setSyncEvents: (value: Event[]) => void;
  recovery: Marker[]; setRecovery: (value: Marker[]) => void; audit: Event[]; setAudit: (value: Event[]) => void;
  settings: Settings; setSettings: (value: Settings) => void; sessionClosed: boolean; setSessionClosed: (value: boolean) => void;
  addProduct: (product: Product) => void; setQty: (sku: string, qty: number) => void; finalizeSale: () => void;
  printReceipt: (label?: string) => void; notify: (message: string) => void; addAudit: (detail: string) => void; logout: () => void;
  subtotal: number; tax: number; total: number;
};

const productRows = [
  ["BR-1001", "Lager 330 ml", "Beer", "330 ml", 120, 18, 42, 12], ["BR-1002", "Pilsner 500 ml", "Beer", "500 ml", 160, 18, 36, 12], ["BR-1003", "Wheat Beer 330 ml", "Beer", "330 ml", 145, 18, 28, 10], ["BR-1004", "Stout 500 ml", "Beer", "500 ml", 190, 18, 8, 10], ["BR-1005", "Light Beer 330 ml", "Beer", "330 ml", 110, 18, 64, 14],
  ["WN-2001", "Red Wine 750 ml", "Wine", "750 ml", 850, 18, 20, 8], ["WN-2002", "White Wine 750 ml", "Wine", "750 ml", 790, 18, 24, 8], ["WN-2003", "Rose Wine 750 ml", "Wine", "750 ml", 820, 18, 16, 8], ["WN-2004", "Sparkling Wine 750 ml", "Wine", "750 ml", 1250, 18, 10, 6], ["WN-2005", "Dessert Wine 375 ml", "Wine", "375 ml", 620, 18, 0, 6],
  ["WK-3001", "Blended Whisky 750 ml", "Whisky", "750 ml", 1450, 18, 22, 8], ["WK-3002", "Premium Whisky 750 ml", "Whisky", "750 ml", 2100, 18, 13, 6], ["WK-3003", "Single Malt 750 ml", "Whisky", "750 ml", 3200, 18, 6, 4], ["WK-3004", "Whisky 375 ml", "Whisky", "375 ml", 760, 18, 18, 8],
  ["VD-4001", "Vodka 750 ml", "Vodka", "750 ml", 980, 18, 31, 10], ["VD-4002", "Vodka 375 ml", "Vodka", "375 ml", 520, 18, 11, 8], ["VD-4003", "Premium Vodka 1 L", "Vodka", "1 L", 1580, 18, 7, 6], ["VD-4004", "Flavoured Vodka 750 ml", "Vodka", "750 ml", 1120, 18, 15, 8],
  ["RM-5001", "Dark Rum 750 ml", "Rum", "750 ml", 760, 18, 27, 10], ["RM-5002", "White Rum 750 ml", "Rum", "750 ml", 780, 18, 19, 10], ["RM-5003", "Spiced Rum 750 ml", "Rum", "750 ml", 920, 18, 5, 6], ["RM-5004", "Rum 375 ml", "Rum", "375 ml", 390, 18, 38, 12],
  ["GN-6001", "Dry Gin 750 ml", "Gin", "750 ml", 1120, 18, 14, 8], ["GN-6002", "Pink Gin 750 ml", "Gin", "750 ml", 1280, 18, 9, 6], ["GN-6003", "Craft Gin 700 ml", "Gin", "700 ml", 1750, 18, 4, 5], ["GN-6004", "Gin 375 ml", "Gin", "375 ml", 590, 18, 21, 8],
  ["BD-7001", "Brandy 750 ml", "Brandy", "750 ml", 890, 18, 17, 8], ["BD-7002", "Premium Brandy 750 ml", "Brandy", "750 ml", 1350, 18, 7, 6], ["BD-7003", "Brandy 375 ml", "Brandy", "375 ml", 460, 18, 25, 10],
  ["RT-8001", "Ready Mix Can 250 ml", "Ready-to-drink", "250 ml", 140, 18, 30, 12], ["RT-8002", "Ready Mix Bottle 330 ml", "Ready-to-drink", "330 ml", 180, 18, 12, 10], ["RT-8003", "Ready Cocktail 275 ml", "Ready-to-drink", "275 ml", 210, 18, 9, 10],
  ["MX-9001", "Soda 750 ml", "Mixers / Non-alcoholic add-ons", "750 ml", 60, 5, 80, 20], ["MX-9002", "Tonic Water 250 ml", "Mixers / Non-alcoholic add-ons", "250 ml", 85, 5, 54, 18], ["MX-9003", "Ginger Ale 250 ml", "Mixers / Non-alcoholic add-ons", "250 ml", 90, 5, 34, 16], ["MX-9004", "Mineral Water 1 L", "Mixers / Non-alcoholic add-ons", "1 L", 40, 5, 100, 24], ["MX-9005", "Non-Alcohol Malt 330 ml", "Mixers / Non-alcoholic add-ons", "330 ml", 90, 5, 48, 18]
];

const seedProducts = productRows.map(([sku, name, category, size, price, tax, stockCount, minimumStock], index) => ({ sku, name, category, size, price, tax, stockCount, minimumStock, ageRestricted: true, batch: `STK-${2400 + index}` })) as Product[];
const customers: Customer[] = ["Walk-in Customer", "Loyalty Customer", "Corporate Event Purchase", "Party Order", "Hotel Account", "Restaurant Account", "Club Member", "Online Pickup", "Caterer Account", "Guest House Account", "Wedding Counter Order", "Staff Authorized Purchase"].map((name, index) => ({ id: `CU-${100 + index}`, name, type: ["Walk-in", "Loyalty", "Corporate", "Event", "Pickup"][index % 5], account: `Counter ${index + 1}`, lastVisit: `Today ${9 + Math.floor(index / 2)}:${index % 2 ? "45" : "10"}` }));
const makeItems = (a: Product, b: Product, qty = 1): CartItem[] => [{ ...a, qty }, { ...b, qty: 1 }];
const seedDrafts = Array.from({ length: 8 }, (_, i) => ({ number: `DS-${1021 + i}`, customer: customers[i].name, items: makeItems(seedProducts[i], seedProducts[i + 8], 1), amount: seedProducts[i].price + seedProducts[i + 8].price, autosaved: `Today ${10 + i}:0${i % 6}`, status: "Open" })) as Draft[];
const seedReceipts = Array.from({ length: 10 }, (_, i) => ({ number: `LR-${2401 + i}`, customer: customers[i % customers.length].name, amount: 900 + i * 185, payment: ["Cash", "Card", "UPI"][i % 3], age: "ID Checked", print: i % 4 === 0 ? "Queued" : "Receipt Printed", sync: i % 3 === 0 ? "Pending" : "Completed", time: `Today ${9 + i}:25`, items: makeItems(seedProducts[i + 2], seedProducts[i + 12]) })) as Receipt[];
const seedJobs = Array.from({ length: 8 }, (_, i) => ({ id: `PJ-${310 + i}`, receipt: `LR-${2401 + i}`, status: ["Printed", "Queued", "Retry"][i % 3], device: "Local Printer", time: `Today ${9 + i}:30` })) as Job[];
const seedSync = Array.from({ length: 8 }, (_, i) => ({ id: `SQ-${410 + i}`, detail: ["Receipt upload", "Stock update", "Audit timeline", "Printer status"][i % 4], status: ["Completed", "Pending", "Retry"][i % 3], time: `Today ${9 + i}:35` })) as Event[];
const seedRecovery = ["open draft", "pending print job", "unsynced receipt", "interrupted sale", "failed print", "stock review pending"].map((type, i) => ({ id: `RC-${510 + i}`, type, detail: `${type} needs review`, status: "Open" })) as Marker[];
const seedAudit = ["login", "age checked", "customer selected", "product added", "draft autosaved", "sale finalized", "receipt printed", "sync retried", "recovery scan completed", "settings saved", "support bundle created", "session closed", "stock reviewed", "receipt viewed", "printer retry"].map((x, i) => ({ id: `AU-${610 + i}`, detail: x, status: "Recorded", time: `Today ${8 + Math.floor(i / 2)}:${i % 2 ? "45" : "15"}` })) as Event[];

function money(value: number) {
  return `₹${Math.round(value)}`;
}

function stockStatus(p: Product) {
  if (p.stockCount <= 0) return "Out of Stock";
  return p.stockCount <= p.minimumStock ? "Low Stock" : "In Stock";
}

export function LiquorDashboard() {
  const router = useRouter();
  const [active, setActive] = useState("Age Verification");
  const [inventory, setInventory] = useState(seedProducts);
  const [selectedCustomer, setSelectedCustomer] = useState(customers[0]);
  const [saleType, setSaleType] = useState("Walk-in");
  const [ageStatus, setAgeStatus] = useState("Not Checked");
  const [dob, setDob] = useState("1990-01-01");
  const [cart, setCart] = useState<CartItem[]>([]);
  const [payment, setPayment] = useState("Cash");
  const [receiptNumber, setReceiptNumber] = useState("Draft Sale");
  const [printStatus, setPrintStatus] = useState("Ready to Print");
  const [drafts, setDrafts] = useState(seedDrafts);
  const [receipts, setReceipts] = useState(seedReceipts);
  const [printerJobs, setPrinterJobs] = useState(seedJobs);
  const [syncEvents, setSyncEvents] = useState(seedSync);
  const [recovery, setRecovery] = useState(seedRecovery);
  const [audit, setAudit] = useState(seedAudit);
  const [settings, setSettings] = useState<Settings>({ store: "HamTech Liquor Counter", counter: "Liquor Counter 1", header: "HamTech POS OS", footer: "Receipt Printed", taxDisplay: "Enabled", printer: "Local thermal", sync: "Offline Sync Queue" });
  const [sessionClosed, setSessionClosed] = useState(false);
  const [toast, setToast] = useState("");

  const subtotal = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.qty, 0), [cart]);
  const tax = useMemo(() => cart.reduce((sum, item) => sum + item.price * item.qty * (item.tax / 100), 0), [cart]);
  const total = subtotal + tax;

  function notify(message: string) {
    setToast(message);
  }

  function addAudit(detail: string) {
    setAudit((items) => [{ id: `AU-${700 + items.length}`, detail, status: "Recorded", time: "Now" }, ...items]);
  }

  function addProduct(product: Product) {
    if (product.stockCount <= 0) return notify("Out of Stock");
    setCart((items) => {
      const existing = items.find((item) => item.sku === product.sku);
      return existing ? items.map((item) => item.sku === product.sku ? { ...item, qty: item.qty + 1 } : item) : [...items, { ...product, qty: 1 }];
    });
    setReceiptNumber("Draft Sale");
    setPrintStatus("Ready to Print");
    addAudit("product added");
    notify("Product added to sale");
  }

  function setQty(sku: string, qty: number) {
    setCart((items) => items.flatMap((item) => item.sku === sku ? (qty > 0 ? [{ ...item, qty }] : []) : [item]));
  }

  function finalizeSale() {
    if (ageStatus !== "ID Checked") return notify("Sale blocked until valid age verification");
    if (!cart.length) return notify("Add products before finalizing sale");
    const blocked = cart.find((item) => inventory.find((p) => p.sku === item.sku && p.stockCount < item.qty));
    if (blocked) return notify("Out of Stock");
    const number = `LR-${2411 + receipts.length}`;
    const receipt: Receipt = { number, customer: selectedCustomer.name, amount: total, payment, age: ageStatus, print: "Queued", sync: "Pending", time: "Now", items: cart };
    setReceipts((items) => [receipt, ...items]);
    setInventory((items) => items.map((p) => {
      const sold = cart.find((item) => item.sku === p.sku);
      return sold ? { ...p, stockCount: p.stockCount - sold.qty } : p;
    }));
    setPrinterJobs((items) => [{ id: `PJ-${400 + items.length}`, receipt: number, status: "Queued", device: "Local Printer", time: "Now" }, ...items]);
    setSyncEvents((items) => [{ id: `SQ-${500 + items.length}`, detail: `${number} receipt upload`, status: "Pending", time: "Now" }, ...items]);
    setReceiptNumber(number);
    setPrintStatus("Queued");
    addAudit("sale finalized");
    notify("Sale finalized");
  }

  function printReceipt(label = "Receipt printed") {
    setPrintStatus("Receipt Printed");
    setPrinterJobs((items) => [{ id: `PJ-${500 + items.length}`, receipt: receiptNumber, status: "Printed", device: "Local Printer", time: "Now" }, ...items]);
    addAudit("receipt printed");
    notify(label);
    window.print();
  }

  function logout() {
    localStorage.removeItem("liquor_pos_cashier");
    router.push("/");
  }

  const api = { active, setActive, inventory, setInventory, selectedCustomer, setSelectedCustomer, saleType, setSaleType, ageStatus, setAgeStatus, dob, setDob, cart, setCart, payment, setPayment, drafts, setDrafts, receipts, setReceipts, printerJobs, setPrinterJobs, syncEvents, setSyncEvents, recovery, setRecovery, audit, setAudit, settings, setSettings, sessionClosed, setSessionClosed, addProduct, setQty, finalizeSale, printReceipt, notify, addAudit, logout, subtotal, tax, total };

  return (
    <main>
      <section className="shell panel">
        <div className="header no-print">
          <div><span className="chip">Liquor Store POS</span><h1>Dashboard</h1><p>HamTech POS OS</p></div>
          <div className="actions"><button type="button" onClick={() => router.back()}>Back</button><button type="button" onClick={() => router.push("/")}>Switch POS</button><button type="button" onClick={logout}>Logout</button></div>
        </div>
        {toast ? <div className="toast">{toast}</div> : null}
        <div className="split-grid">
          <div className="no-print">
            <div className="module-grid">{modules.map((name) => <button className={`module-card ${active === name ? "primary featured" : ""}`} key={name} type="button" onClick={name === "Logout" ? logout : () => setActive(name)}><span className="label">Module</span><span className="value">{name}</span></button>)}</div>
            <Panel api={api} />
          </div>
          <Receipt settings={settings} customer={selectedCustomer.name} ageStatus={ageStatus} cart={cart} subtotal={subtotal} tax={tax} total={total} payment={payment} receiptNumber={receiptNumber} printStatus={printStatus} printReceipt={printReceipt} />
        </div>
      </section>
    </main>
  );
}

function Panel({ api }: { api: DashboardApi }) {
  if (api.active === "Age Verification") return <Block title="Age Verification"><div className="status-grid"><Metric label="Current sale status" value={api.ageStatus === "ID Checked" ? "Sale Allowed" : "Sale Blocked"} /><Metric label="ID checked" value={api.ageStatus} /><label><span className="label">DOB</span><input type="date" value={api.dob} onChange={(e) => api.setDob(e.target.value)} /></label></div><div className="actions"><button onClick={() => { api.setAgeStatus("ID Checked"); api.addAudit("age checked"); api.notify("Age verification completed"); }}>Mark ID Checked</button><button className="secondary" onClick={() => { api.setAgeStatus("Sale Blocked"); api.notify("Sale blocked until valid age verification"); }}>Block Sale</button><button className="secondary" onClick={() => { api.setAgeStatus("Not Checked"); api.notify("Verification reset"); }}>Reset Verification</button></div><Rows rows={api.audit.slice(0, 5).map((x) => [x.time, x.detail, x.status])} /></Block>;
  if (api.active === "Customer / Counter Sale") return <CustomerPanel api={api} />;
  if (api.active === "Product Lookup") return <ProductPanel api={api} />;
  if (api.active === "Stock Check") return <StockPanel api={api} />;
  if (api.active === "New Sale") return <SalePanel api={api} />;
  if (api.active === "Draft Sales") return <Block title="Draft Sales"><Rows rows={api.drafts.map((d) => [d.number, `${d.customer} · ${d.items.length} items · ${money(d.amount)} · ${d.autosaved}`, d.status])} /><div className="actions"><button onClick={() => { const d = api.drafts[0]; api.setCart(d.items); api.setSelectedCustomer(customers.find((c) => c.name === d.customer) ?? customers[0]); api.setActive("New Sale"); api.notify("Draft loaded"); }}>Continue Draft</button><button className="secondary" onClick={() => { api.setDrafts(api.drafts.map((d, i) => i === 0 ? { ...d, status: "Voided" } : d)); api.notify("Draft voided"); }}>Void Draft</button></div></Block>;
  if (api.active === "Bills / Receipts") return <Block title="Bills / Receipts"><Rows rows={api.receipts.map((r) => [r.number, `${r.customer} · ${money(r.amount)} · ${r.payment} · ${r.age}`, `${r.print} · ${r.sync} · ${r.time}`])} /><div className="actions"><button onClick={() => { const r = api.receipts[0]; api.setCart(r.items); api.setSelectedCustomer(customers.find((c) => c.name === r.customer) ?? customers[0]); api.notify("Receipt loaded"); }}>View Receipt</button><button className="secondary" onClick={() => api.printReceipt("Receipt printed")}>Reprint Receipt</button></div></Block>;
  if (api.active === "Printer") return <Block title="Printer"><Metric label="Local Printer" value="Active" /><Rows rows={api.printerJobs.map((j) => [j.id, `${j.receipt} · ${j.device} · ${j.time}`, j.status])} /><div className="actions"><button onClick={() => api.printReceipt("Receipt printed")}>Print Current Receipt</button><button className="secondary" onClick={() => api.printReceipt("Receipt printed")}>Reprint Last Receipt</button><button className="secondary" onClick={() => { api.setPrinterJobs(api.printerJobs.map((j) => j.status === "Retry" ? { ...j, status: "Queued" } : j)); api.notify("Printer job queued"); }}>Retry Failed Job</button></div></Block>;
  if (api.active === "Sync") return <Block title="Sync"><div className="status-grid"><Metric label="Offline Sync Queue" value={`${api.syncEvents.filter((e) => e.status !== "Completed").length} pending`} /><Metric label="Completed" value={String(api.syncEvents.filter((e) => e.status === "Completed").length)} /></div><Rows rows={api.syncEvents.map((e) => [e.id, `${e.detail} · ${e.time}`, e.status])} /><div className="actions"><button onClick={() => { api.setSyncEvents(api.syncEvents.map((e) => ({ ...e, status: "Completed" }))); api.addAudit("sync retried"); api.notify("Sync queue updated"); }}>Retry All</button><button className="secondary" onClick={() => { api.setSyncEvents(api.syncEvents.map((e, i) => i === 0 ? { ...e, status: "Completed" } : e)); api.notify("Sync queue updated"); }}>Retry Single Event</button></div></Block>;
  if (api.active === "Recovery") return <Block title="Recovery"><Rows rows={api.recovery.map((m) => [m.id, `${m.type} · ${m.detail}`, m.status])} /><div className="actions"><button onClick={() => { api.addAudit("recovery scan completed"); api.notify("Recovery scan completed"); }}>Run Recovery Scan</button><button className="secondary" onClick={() => { api.setRecovery(api.recovery.map((m) => ({ ...m, status: "Reviewed" }))); api.notify("Recovery marker reviewed"); }}>Mark Reviewed</button><button className="secondary" onClick={() => { api.setRecovery(api.recovery.map((m, i) => i === 0 ? { ...m, status: "Resolved" } : m)); api.notify("Recovery marker resolved"); }}>Resolve Marker</button></div></Block>;
  if (api.active === "Reports") return <Reports api={api} />;
  if (api.active === "Settings") return <SettingsPanel api={api} />;
  if (api.active === "Support") return <Block title="Support"><Rows rows={[["API/UI", "Healthy", "Ready"], ["Local Printer", "Active", "Ready"], ["Offline Sync Queue", "Healthy", "Ready"], ["Local storage", "Ready", "Ready"], ["Last backup", "BK-2026-0701", "Available"], ["Support bundle", "SB-2407", "Ready"]]} /><button onClick={() => { api.addAudit("support bundle created"); api.notify("Support bundle created"); }}>Create Support Bundle</button></Block>;
  if (api.active === "Audit") return <Block title="Audit"><Rows rows={api.audit.map((a) => [a.time, a.detail, a.status])} /><div className="actions"><button onClick={() => { api.addAudit("audit note added"); api.notify("Audit note added"); }}>Add Audit Note</button><button className="secondary" onClick={() => api.notify("Timeline refreshed")}>Refresh Timeline</button></div></Block>;
  if (api.active === "Close Session") return <CloseSession api={api} />;
  return <Block title={api.active}><Rows rows={[["Cashier", "Cashier", "Active"], ["Counter", api.settings.counter, "Ready"], ["Support", "HamTech Innovations", "Available"]]} /></Block>;
}

function CustomerPanel({ api }: { api: DashboardApi }) {
  const [query, setQuery] = useState("");
  const rows = customers.filter((c) => c.name.toLowerCase().includes(query.toLowerCase()) || c.type.toLowerCase().includes(query.toLowerCase()));
  return <Block title="Customer / Counter Sale"><div className="status-grid"><label><span className="label">Search customer/context</span><input value={query} onChange={(e) => setQuery(e.target.value)} /></label><label><span className="label">Sale type</span><select value={api.saleType} onChange={(e) => api.setSaleType(e.target.value)}>{["Walk-in", "Loyalty", "Corporate", "Event", "Pickup"].map((x) => <option key={x}>{x}</option>)}</select></label><Metric label="Selected customer" value={api.selectedCustomer.name} /></div><Rows rows={rows.map((c) => [c.id, `${c.name} · ${c.type} · ${c.lastVisit}`, c.account])} /><div className="actions"><button onClick={() => { api.setSelectedCustomer(rows[0] ?? customers[0]); api.addAudit("customer selected"); api.notify("Customer selected"); }}>Select Customer</button><button className="secondary" onClick={() => { api.setSelectedCustomer(customers[0]); api.setActive("New Sale"); api.notify("Counter sale started"); }}>Start Counter Sale</button></div></Block>;
}

function ProductPanel({ api }: { api: DashboardApi }) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const rows = api.inventory.filter((p) => (category === "All" || p.category === category) && `${p.sku} ${p.name}`.toLowerCase().includes(query.toLowerCase()));
  return <Block title="Product Lookup"><div className="status-grid"><label><span className="label">Search products</span><input value={query} onChange={(e) => setQuery(e.target.value)} /></label><label><span className="label">Category filter</span><select value={category} onChange={(e) => setCategory(e.target.value)}>{categories.map((x) => <option key={x}>{x}</option>)}</select></label><Metric label="Products shown" value={String(rows.length)} /></div><Rows rows={rows.map((p) => [p.sku, `${p.name} · ${p.category} · ${p.size} · ${money(p.price)} · tax ${p.tax}%`, `${p.stockCount} · ${stockStatus(p)}`])} /><div className="actions"><button onClick={() => api.addProduct(rows[0] ?? api.inventory[0])}>Add to Sale</button><button className="secondary" onClick={() => api.notify(`${(rows[0] ?? api.inventory[0]).name} viewed`)}>View Product</button><button className="secondary" onClick={() => setCategory("Wine")}>Filter by Category</button></div></Block>;
}

function StockPanel({ api }: { api: DashboardApi }) {
  const low = api.inventory.filter((p) => stockStatus(p) === "Low Stock");
  return <Block title="Stock Check"><div className="status-grid"><Metric label="Total products" value={String(api.inventory.length)} /><Metric label="Low stock" value={String(low.length)} /><Metric label="Out of stock" value={String(api.inventory.filter((p) => stockStatus(p) === "Out of Stock").length)} /><Metric label="In stock" value={String(api.inventory.filter((p) => stockStatus(p) === "In Stock").length)} /></div><h3>Low stock section</h3><Rows rows={low.map((p) => [p.sku, `${p.name} · minimum ${p.minimumStock}`, `${p.stockCount} · ${stockStatus(p)}`])} /><Rows rows={api.inventory.slice(0, 12).map((p) => [p.sku, `${p.name} · ${p.batch}`, `${p.stockCount} · ${stockStatus(p)}`])} /><button onClick={() => { api.addAudit("stock reviewed"); api.notify("Stock reviewed"); }}>Mark Stock Reviewed</button></Block>;
}

function SalePanel({ api }: { api: DashboardApi }) {
  return <Block title="New Sale"><div className="status-grid"><Metric label="Selected customer" value={api.selectedCustomer.name} /><Metric label="Age verification" value={api.ageStatus} /><label><span className="label">Payment method</span><select value={api.payment} onChange={(e) => api.setPayment(e.target.value)}>{["Cash", "Card", "UPI"].map((x) => <option key={x}>{x}</option>)}</select></label></div><Rows rows={api.cart.map((item) => [item.sku, `${item.name} · ${money(item.price)} · qty ${item.qty}`, money(item.price * item.qty)])} /><div className="actions">{api.cart.map((item) => <span key={item.sku} className="actions"><button onClick={() => api.setQty(item.sku, item.qty + 1)}>+</button><button className="secondary" onClick={() => api.setQty(item.sku, item.qty - 1)}>-</button><button className="secondary" onClick={() => api.setQty(item.sku, 0)}>Remove {item.sku}</button></span>)}</div><h3>Product suggestions</h3><div className="actions">{api.inventory.slice(0, 8).map((p) => <button key={p.sku} type="button" onClick={() => api.addProduct(p)}>{p.name}</button>)}</div><Rows rows={[["Subtotal", money(api.subtotal), "Current sale"], ["Tax", money(api.tax), "Calculated"], ["Total", money(api.total), "Ready"]]} /><button onClick={api.finalizeSale}>Finalize Sale</button></Block>;
}

function Reports({ api }: { api: DashboardApi }) {
  const split = ["Cash", "Card", "UPI"].map((p) => [p, api.receipts.filter((r) => r.payment === p).reduce((s, r) => s + r.amount, 0)]);
  const categorySales = categories.slice(1, 9).map((category) => [category, api.receipts.reduce((sum, receipt) => sum + receipt.items.filter((item) => item.category === category).reduce((s, item) => s + item.price * item.qty, 0), 0)]);
  const today = api.receipts.reduce((sum, r) => sum + r.amount, api.total);
  return <Block title="Reports"><div className="status-grid"><Metric label="Today sales" value={money(today)} /><Metric label="Receipt count" value={String(api.receipts.length)} /><Metric label="Average sale" value={money(today / Math.max(api.receipts.length, 1))} /><Metric label="Low stock count" value={String(api.inventory.filter((p) => stockStatus(p) !== "In Stock").length)} /></div><h3>Cash/Card/UPI split</h3><Bars rows={split} /><h3>Category sales</h3><Bars rows={categorySales} /><h3>Top products</h3><Rows rows={api.inventory.slice(0, 8).map((p) => [p.sku, p.name, money(p.price)])} /></Block>;
}

function SettingsPanel({ api }: { api: DashboardApi }) {
  const fields: [keyof Settings, string][] = [["store", "Store name"], ["counter", "Counter name"], ["header", "Receipt header"], ["footer", "Receipt footer"], ["taxDisplay", "Tax display"], ["printer", "Printer profile"], ["sync", "Sync mode"]];
  return <Block title="Settings"><div className="form-grid">{fields.map(([key, label]) => <label key={key}><span className="label">{label}</span><input value={api.settings[key]} onChange={(e) => api.setSettings({ ...api.settings, [key]: e.target.value })} /></label>)}</div><button onClick={() => { api.addAudit("settings saved"); api.notify("Settings saved"); }}>Save Settings</button></Block>;
}

function CloseSession({ api }: { api: DashboardApi }) {
  const cash = api.receipts.filter((r) => r.payment === "Cash").reduce((s, r) => s + r.amount, 0);
  const card = api.receipts.filter((r) => r.payment === "Card").reduce((s, r) => s + r.amount, 0);
  const upi = api.receipts.filter((r) => r.payment === "UPI").reduce((s, r) => s + r.amount, 0);
  return <Block title="Close Session"><Rows rows={[["Opening cash", "₹5000", api.sessionClosed ? "Closed" : "Open"], ["Cash sales", money(cash), "Counted"], ["Card sales", money(card), "Settled"], ["UPI sales", money(upi), "Settled"], ["Total sales", money(cash + card + upi), "Today"], ["Receipt count", String(api.receipts.length), "Finalized"], ["Expected cash", money(5000 + cash), "Balanced"], ["Difference", "₹0", "Ready"]]} /><button onClick={() => { api.setSessionClosed(true); api.addAudit("session closed"); api.notify("Session closed"); }}>Close Session</button></Block>;
}

function Receipt({ settings, customer, ageStatus, cart, subtotal, tax, total, payment, receiptNumber, printStatus, printReceipt }: { settings: Settings; customer: string; ageStatus: string; cart: CartItem[]; subtotal: number; tax: number; total: number; payment: string; receiptNumber: string; printStatus: string; printReceipt: () => void }) {
  return <aside className="receipt-paper"><header><h1>{settings.header}</h1><p>{settings.store}</p><p>Liquor Store POS</p><p>Receipt Preview</p></header><div className="receipt-lines"><div className="receipt-line"><span>Receipt</span><strong>{receiptNumber}</strong></div><div className="receipt-line"><span>Cashier / Counter</span><strong>Cashier / {settings.counter}</strong></div><div className="receipt-line"><span>Customer</span><strong>{customer}</strong></div><div className="receipt-line"><span>Age verification</span><strong>{ageStatus}</strong></div></div>{cart.length ? cart.map((item) => <div className="receipt-item" key={item.sku}><span>{item.name}</span><span>{item.qty} x {item.size}</span><strong>{money(item.price * item.qty)}</strong></div>) : <p>No sale items added.</p>}<div className="receipt-lines totals"><div className="receipt-line"><span>Subtotal</span><strong>{money(subtotal)}</strong></div><div className="receipt-line"><span>Tax</span><strong>{money(tax)}</strong></div><div className="receipt-line"><span>Total</span><strong>{money(total)}</strong></div><div className="receipt-line"><span>Payment method</span><strong>{payment}</strong></div><div className="receipt-line"><span>Payment status</span><strong>{receiptNumber === "Draft Sale" ? "Awaiting finalization" : "Paid"}</strong></div><div className="receipt-line"><span>Print status</span><strong>{printStatus}</strong></div></div><footer><p>{settings.footer}</p><div className="actions no-print"><button type="button" onClick={() => printReceipt()}>Print Receipt</button><button className="secondary" type="button" onClick={() => printReceipt()}>Save as PDF</button></div></footer></aside>;
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="status-item" style={{ marginTop: 16, overflowX: "auto" }}><h2>{title}</h2>{children}</section>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div className="status-item"><span className="label">{label}</span><span className="value">{value}</span></div>;
}

function Rows({ rows }: { rows: string[][] }) {
  return <div className="receipt-lines">{rows.map((row) => <div className="receipt-line" key={row.join("-")}><span>{row[0]}</span><span>{row[1]}</span><strong>{row[2]}</strong></div>)}</div>;
}

function Bars({ rows }: { rows: (string | number)[][] }) {
  const max = Math.max(...rows.map(([, value]) => Number(value)), 1);
  return <div className="receipt-lines">{rows.map(([label, value]) => <div key={String(label)}><div className="receipt-line"><span>{label}</span><strong>{money(Number(value))}</strong></div><div style={{ background: "rgba(15,118,110,.12)", borderRadius: 999, height: 10 }}><div style={{ width: `${Math.max(8, Number(value) / max * 100)}%`, background: "var(--accent)", borderRadius: 999, height: 10 }} /></div></div>)}</div>;
}

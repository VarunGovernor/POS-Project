"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const modules = [
  "Age Verification",
  "Customer / Counter Sale",
  "Product Lookup",
  "Stock Check",
  "New Sale",
  "Draft Sales",
  "Bills / Receipts",
  "Printer",
  "Sync",
  "Recovery",
  "Reports",
  "Settings",
  "Support",
  "Audit",
  "Close Session",
  "Logout"
];

const products = [
  ["BR-1001", "Lager 330 ml", "Beer", "330 ml", 120, 42],
  ["BR-1002", "Pilsner 500 ml", "Beer", "500 ml", 160, 36],
  ["BR-1003", "Wheat Beer 330 ml", "Beer", "330 ml", 145, 28],
  ["BR-1004", "Stout 500 ml", "Beer", "500 ml", 190, 18],
  ["BR-1005", "Light Beer 330 ml", "Beer", "330 ml", 110, 64],
  ["WN-2001", "Red Wine 750 ml", "Wine", "750 ml", 850, 20],
  ["WN-2002", "White Wine 750 ml", "Wine", "750 ml", 790, 24],
  ["WN-2003", "Rose Wine 750 ml", "Wine", "750 ml", 820, 16],
  ["WN-2004", "Sparkling Wine 750 ml", "Wine", "750 ml", 1250, 10],
  ["WN-2005", "Dessert Wine 375 ml", "Wine", "375 ml", 620, 12],
  ["SP-3001", "Whisky 750 ml", "Spirits", "750 ml", 1450, 22],
  ["SP-3002", "Vodka 750 ml", "Spirits", "750 ml", 980, 31],
  ["SP-3003", "Rum 750 ml", "Spirits", "750 ml", 760, 27],
  ["SP-3004", "Gin 750 ml", "Spirits", "750 ml", 1120, 14],
  ["SP-3005", "Brandy 750 ml", "Spirits", "750 ml", 890, 17],
  ["SP-3006", "Tequila 750 ml", "Spirits", "750 ml", 1680, 9],
  ["BR-1006", "Craft IPA 330 ml", "Beer", "330 ml", 220, 21],
  ["WN-2006", "Table Wine 750 ml", "Wine", "750 ml", 560, 30],
  ["SP-3007", "Single Malt 750 ml", "Spirits", "750 ml", 3200, 6],
  ["BR-1007", "Non-Alcohol Malt 330 ml", "Beer", "330 ml", 90, 48],
  ["SP-3008", "Liqueur 700 ml", "Spirits", "700 ml", 1320, 11]
].map(([sku, name, category, size, price, stock]) => ({ sku, name, category, size, price, stock, restricted: category !== "Beer" || name !== "Non-Alcohol Malt 330 ml" })) as Product[];

const drafts = ["DS-1021 Counter sale, 2 items", "DS-1022 ID checked, awaiting payment"];
const receipts = ["LR-2401 Paid, Receipt Printed", "LR-2402 Paid, Receipt Printed"];
const printerQueue = ["LR-2403 Local Printer queued", "LR-2402 Receipt Printed"];
const audit = ["09:10 Session opened", "09:14 ID Checked", "09:16 Sale Allowed", "09:20 Receipt Printed"];
const reports = ["Beer category sales: 18 units", "Wine category sales: 7 units", "Spirits category sales: 9 units"];

type Product = { sku: string; name: string; category: string; size: string; price: number; stock: number; restricted: boolean };

export function LiquorDashboard() {
  const router = useRouter();
  const [active, setActive] = useState("Age Verification");
  const [ageStatus, setAgeStatus] = useState("ID Checked");
  const [cart, setCart] = useState<Product[]>([products[0]]);
  const [finalized, setFinalized] = useState(false);
  const [receiptPrinted, setReceiptPrinted] = useState(false);
  const subtotal = useMemo(() => cart.reduce((sum, item) => sum + item.price, 0), [cart]);
  const tax = Math.round(subtotal * 0.18);
  const total = subtotal + tax;

  function printReceipt() {
    setReceiptPrinted(true);
    window.print();
  }

  function logout() {
    localStorage.removeItem("liquor_pos_cashier");
    router.push("/");
  }

  return (
    <main>
      <section className="shell panel">
        <div className="header no-print">
          <div>
            <span className="chip">Liquor Store POS</span>
            <h1>Dashboard</h1>
            <p>HamTech POS OS</p>
          </div>
          <div className="actions">
            <button type="button" onClick={() => router.back()}>Back</button>
            <button type="button" onClick={() => router.push("/")}>Switch POS</button>
            <button type="button" onClick={logout}>Logout</button>
          </div>
        </div>
        <div className="split-grid">
          <div className="no-print">
            <div className="module-grid">
              {modules.map((name) => (
                <button className={`module-card ${active === name ? "primary featured" : ""}`} key={name} type="button" onClick={name === "Logout" ? logout : () => setActive(name)}>
                  <span className="label">Module</span>
                  <span className="value">{name}</span>
                </button>
              ))}
            </div>
            <Panel active={active} ageStatus={ageStatus} setAgeStatus={setAgeStatus} cart={cart} setCart={setCart} finalized={finalized} setFinalized={setFinalized} />
          </div>
          <Receipt ageStatus={ageStatus} cart={cart} subtotal={subtotal} tax={tax} total={total} finalized={finalized} receiptPrinted={receiptPrinted} printReceipt={printReceipt} />
        </div>
      </section>
    </main>
  );
}

function Panel({ active, ageStatus, setAgeStatus, cart, setCart, finalized, setFinalized }: { active: string; ageStatus: string; setAgeStatus: (value: string) => void; cart: Product[]; setCart: (value: Product[]) => void; finalized: boolean; setFinalized: (value: boolean) => void }) {
  if (active === "Age Verification") return <Block title="Age Verification"><button onClick={() => setAgeStatus("Sale Allowed")}>ID Checked</button><button className="secondary" onClick={() => setAgeStatus("Sale Blocked")}>Sale Blocked</button><p>{ageStatus}</p></Block>;
  if (active === "Product Lookup" || active === "Stock Check") return <Block title={active}><Rows rows={products.map((p) => [p.sku, `${p.name} · ${p.size} · ${p.category}`, `Stock Available: ${p.stock}`])} /></Block>;
  if (active === "New Sale") return <Block title="New Sale"><div className="actions">{products.slice(0, 6).map((p) => <button key={p.sku} type="button" onClick={() => { setCart([...cart, p]); setFinalized(false); }}>{p.name}</button>)}<button type="button" onClick={() => setFinalized(true)}>Finalize Sale</button></div><p>{cart.length} products added. {finalized ? "Receipt Preview ready." : "Awaiting finalization."}</p></Block>;
  if (active === "Draft Sales") return <Block title="Draft Sales"><Rows rows={drafts.map((x) => ["Draft", x, "Open"])} /></Block>;
  if (active === "Bills / Receipts") return <Block title="Bills / Receipts"><Rows rows={receipts.map((x) => ["Receipt", x, "Paid"])} /></Block>;
  if (active === "Printer") return <Block title="Printer"><Rows rows={printerQueue.map((x) => ["Local Printer", x, "Ready"])} /></Block>;
  if (active === "Sync") return <Block title="Sync"><Rows rows={[["Sync Queue", "2 receipts pending upload", "Ready"], ["Last sync", "Today 09:30", "Complete"]]} /></Block>;
  if (active === "Recovery") return <Block title="Recovery"><Rows rows={[["Recovery", "1 draft sale recoverable", "Review"], ["Cash drawer", "Balanced", "Complete"]]} /></Block>;
  if (active === "Reports") return <Block title="Reports"><Rows rows={reports.map((x) => ["Category sales", x, "Today"])} /></Block>;
  if (active === "Audit") return <Block title="Audit"><Rows rows={audit.map((x) => ["Timeline", x, "Recorded"])} /></Block>;
  if (active === "Close Session") return <Block title="Close Session"><Rows rows={[["Counter", "Liquor Counter 1", "Open"], ["Expected cash", "Matches paid receipts", "Ready to close"]]} /></Block>;
  return <Block title={active}><Rows rows={[["Cashier", "Cashier", "Active"], ["Counter", "Liquor Counter 1", "Ready"], ["Support", "HamTech Innovations", "Available"]]} /></Block>;
}

function Receipt({ ageStatus, cart, subtotal, tax, total, finalized, receiptPrinted, printReceipt }: { ageStatus: string; cart: Product[]; subtotal: number; tax: number; total: number; finalized: boolean; receiptPrinted: boolean; printReceipt: () => void }) {
  return (
    <aside className="receipt-paper">
      <header><h1>HamTech POS OS</h1><p>Liquor Store POS</p><p>Receipt Preview</p></header>
      <div className="receipt-lines">
        <div className="receipt-line"><span>Receipt</span><strong>LR-2404</strong></div>
        <div className="receipt-line"><span>Cashier / Counter</span><strong>Cashier / Liquor Counter 1</strong></div>
        <div className="receipt-line"><span>Age verification</span><strong>{ageStatus}</strong></div>
      </div>
      {cart.map((item, index) => <div className="receipt-item" key={`${item.sku}-${index}`}><span>{item.name}</span><span>{item.size}</span><strong>₹{item.price}</strong></div>)}
      <div className="receipt-lines totals">
        <div className="receipt-line"><span>Subtotal</span><strong>₹{subtotal}</strong></div>
        <div className="receipt-line"><span>Tax</span><strong>₹{tax}</strong></div>
        <div className="receipt-line"><span>Total</span><strong>₹{total}</strong></div>
        <div className="receipt-line"><span>Payment status</span><strong>{finalized ? "Paid" : "Awaiting finalization"}</strong></div>
        <div className="receipt-line"><span>Print status</span><strong>{receiptPrinted ? "Receipt Printed" : "Ready to Print"}</strong></div>
      </div>
      <footer className="no-print"><button type="button" onClick={printReceipt}>Print Receipt</button><button className="secondary" type="button" onClick={printReceipt}>Save as PDF</button></footer>
    </aside>
  );
}

function Block({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="status-item" style={{ marginTop: 16 }}><h2>{title}</h2>{children}</section>;
}

function Rows({ rows }: { rows: string[][] }) {
  return <div className="receipt-lines">{rows.map((row) => <div className="receipt-line" key={row.join("-")}><span>{row[0]}</span><span>{row[1]}</span><strong>{row[2]}</strong></div>)}</div>;
}

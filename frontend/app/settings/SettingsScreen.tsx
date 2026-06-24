"use client";

import { useEffect, useState } from "react";

import { ScreenNavActions } from "@/app/components/ScreenNavActions";
import { SettingItem, localApi } from "@/lib/api/client";

function token() {
  return typeof window === "undefined" ? null : localStorage.getItem("counteros_token");
}

export function SettingsScreen() {
  const [items, setItems] = useState<SettingItem[]>([]);
  const [message, setMessage] = useState("");
  const [state, setState] = useState<"loading" | "ready" | "api-unavailable" | "permission-denied" | "error">("loading");

  async function load() {
    setState("loading");
    setMessage("");
    try {
      setItems((await localApi.settings(token())).data.items);
      setState("ready");
    } catch (error) {
      const text = error instanceof Error ? error.message : "Settings load failed.";
      if (text.includes("AUTH_PERMISSION_DENIED")) setState("permission-denied");
      else setState(text.toLowerCase().includes("fetch") ? "api-unavailable" : "error");
      setMessage(text);
    }
  }

  async function save(item: SettingItem, value: string) {
    try {
      await localApi.updateSetting(token(), { setting_key: item.setting_key, setting_value: value, setting_scope: item.setting_scope });
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Update failed.");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (state === "loading") return <main><section className="shell panel"><h1>Settings</h1><p>Loading.</p></section></main>;
  if (state === "api-unavailable") return <main><section className="shell panel"><h1>Settings</h1><p className="error-text">API unavailable.</p></section></main>;
  if (state === "permission-denied") return <main><section className="shell panel"><h1>Settings</h1><p className="error-text">Permission denied.</p></section></main>;
  if (state === "error") return <main><section className="shell panel"><h1>Settings</h1><p className="error-text">{message}</p></section></main>;

  return (
    <main>
      <section className="shell panel">
        <div className="header"><h1>Settings</h1><div className="actions screen-nav"><ScreenNavActions /><button type="button" onClick={load}>Refresh</button></div></div>
        {message ? <p className="error-text">{message}</p> : null}
        {items.length === 0 ? <p>No settings.</p> : null}
        <div className="status-grid">
          {items.map((item) => (
            <form className="status-item" key={item.id} onSubmit={(event) => {
              event.preventDefault();
              const value = new FormData(event.currentTarget).get("value")?.toString() ?? "";
              void save(item, value);
            }}>
              <span className="label">{item.setting_key}</span>
              <input name="value" defaultValue={item.setting_value} disabled={item.is_readonly} />
              <span className="value">{item.is_readonly ? "readonly" : item.setting_scope}</span>
              {!item.is_readonly ? <button type="submit">Save</button> : null}
            </form>
          ))}
        </div>
      </section>
    </main>
  );
}

import { useEffect, useState } from "react";
import { api, useApi } from "../../api.js";
import { Empty, ErrorNote, Loading } from "../Status.jsx";
import { CATEGORY_NAMES } from "./categories.js";

const FILTERS = [
  ["all", "All"],
  ["pending", "Waiting for review"],
  ["published", "On the website"],
];

/** Aircraft management (admin only): review scraped aircraft, edit details, upload photos. */
export default function Products({ token }) {
  const [filter, setFilter] = useState("pending");
  const [reload, setReload] = useState(0);
  const [editing, setEditing] = useState(null); // slug, "new", or null
  const list = useApi(`/api/admin/products?status=${filter}`, { token, reload });
  const refresh = () => setReload((n) => n + 1);

  return (
    <div className="grid gap-8">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div role="group" aria-label="Filter aircraft" className="flex flex-wrap gap-2">
          {FILTERS.map(([key, label]) => (
            <button key={key} onClick={() => setFilter(key)} aria-pressed={filter === key}
              className={`border px-3 py-1.5 font-display text-[1.05rem] ${filter === key ? "border-ink bg-ink text-chart" : "border-rule bg-paper"}`}>
              {label}
            </button>
          ))}
        </div>
        <button className="btn" onClick={() => setEditing("new")}>Add an aircraft</button>
      </div>

      {editing === "new" && (
        <ProductForm token={token} onDone={(slug) => { setEditing(slug); refresh(); }} onCancel={() => setEditing(null)} />
      )}
      {editing && editing !== "new" && (
        <ProductForm key={editing} slug={editing} token={token} onDone={refresh} onCancel={() => setEditing(null)} />
      )}

      {list.loading && <Loading what="aircraft" />}
      {list.error && <ErrorNote error={list.error} />}
      {list.data && list.data.length === 0 && (
        <Empty title="Nothing here">Scraped aircraft wait here for review before they go on the website.</Empty>
      )}
      {list.data?.length > 0 && (
        <div className="overflow-x-auto border border-rule bg-paper">
          <table className="w-full min-w-[46rem] text-left">
            <thead className="border-b border-rule font-display text-lg text-soft">
              <tr>
                <th className="p-3">Aircraft</th>
                <th className="p-3">Category</th>
                <th className="p-3">Price</th>
                <th className="p-3">Photo</th>
                <th className="p-3">Status</th>
                <th className="p-3"><span className="sr-only">Actions</span></th>
              </tr>
            </thead>
            <tbody>
              {list.data.map((d) => (
                <tr key={d.slug} className="border-b border-rule last:border-0">
                  <td className="p-3">
                    <p className="font-display text-lg">{d.name}</p>
                    <p className="text-[0.9rem] text-soft">{d.manufacturer}{d.manual_edit ? " · edited by hand" : ""}</p>
                  </td>
                  <td className="p-3">{d.category}</td>
                  <td className="tabular p-3">{d.price_usd ? `US$${d.price_usd.toLocaleString("en-US")}` : "On request"}</td>
                  <td className="p-3">{d.image_url ? "Yes" : <span className="text-route">Missing</span>}</td>
                  <td className="p-3">{d.status === "published" ? "On website" : "Waiting"}</td>
                  <td className="p-3 text-right whitespace-nowrap">
                    <button className="link mr-4" onClick={() => setEditing(d.slug)}>Edit</button>
                    <StatusButton token={token} drone={d} onChanged={refresh} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatusButton({ token, drone, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const publish = drone.status !== "published";

  async function toggle() {
    setBusy(true);
    setError("");
    try {
      await api(`/api/admin/products/${encodeURIComponent(drone.slug)}/status`, {
        method: "POST", token, body: { status: publish ? "published" : "pending" },
      });
      onChanged();
    } catch (err) {
      setError(err.detail);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button className="link" disabled={busy} onClick={toggle}>{publish ? "Publish" : "Take down"}</button>
      {error && <span role="alert" className="ml-2 text-route">{error}</span>}
    </>
  );
}

function ProductForm({ slug, token, onDone, onCancel }) {
  const isNew = !slug;
  const blank = { name: "", manufacturer: "", category: CATEGORY_NAMES[0], status: "pending", price_usd: "",
                  description: "", specs: "{}", image_credit: "", source_url: "" };
  const [form, setForm] = useState(blank);
  const [loaded, setLoaded] = useState(isNew);
  const [state, setState] = useState({ status: "idle", message: "" });
  const [photo, setPhoto] = useState({ status: "idle", message: "" });
  const [current, setCurrent] = useState(null);
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  // Load the existing aircraft once. The parent gives each aircraft its own key, so this runs per aircraft.
  useEffect(() => {
    if (isNew) return undefined;
    const controller = new AbortController();
    api(`/api/admin/products/${encodeURIComponent(slug)}`, { token, signal: controller.signal })
      .then((d) => {
        setCurrent(d);
        setForm({
          name: d.name, manufacturer: d.manufacturer, category: d.category, status: d.status,
          price_usd: d.price_usd ?? "", description: d.description || "",
          specs: JSON.stringify(d.specs || {}, null, 2), image_credit: d.image_credit || "", source_url: d.source_url || "",
        });
        setLoaded(true);
      })
      .catch((err) => {
        if (err.name === "AbortError") return;
        setState({ status: "error", message: err.detail || err.message });
        setLoaded(true);
      });
    return () => controller.abort();
  }, [slug, token, isNew]);

  function payload() {
    let specs;
    try {
      specs = JSON.parse(form.specs || "{}");
    } catch {
      throw new Error("Specs must be valid JSON, for example {\"flight_time_min\": 40}.");
    }
    const body = {
      name: form.name, manufacturer: form.manufacturer, category: form.category,
      description: form.description, specs,
      price_usd: form.price_usd === "" ? null : Number(form.price_usd),
      image_credit: form.image_credit || null, source_url: form.source_url || null,
    };
    if (isNew) body.status = form.status;
    return body;
  }

  async function save(event) {
    event.preventDefault();
    setState({ status: "saving", message: "" });
    try {
      const body = payload();
      const result = isNew
        ? await api("/api/admin/products", { method: "POST", token, body })
        : await api(`/api/admin/products/${encodeURIComponent(slug)}`, { method: "PUT", token, body });
      setCurrent(result);
      setState({ status: "saved", message: "Saved." });
      onDone(result.slug);
    } catch (err) {
      setState({ status: "error", message: err.detail || err.message });
    }
  }

  async function uploadPhoto(event) {
    const file = event.target.files?.[0];
    if (!file || !current) return;
    setPhoto({ status: "uploading", message: "" });
    try {
      const response = await fetch(`/api/admin/products/${encodeURIComponent(current.slug)}/image`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": file.type },
        body: file,
      });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || "The photo could not be uploaded.");
      setCurrent(data);
      setPhoto({ status: "done", message: "Photo updated." });
      onDone(data.slug);
    } catch (err) {
      setPhoto({ status: "error", message: err.message });
    } finally {
      event.target.value = "";
    }
  }

  if (!loaded) return <Loading what="aircraft" />;

  return (
    <section aria-labelledby="pf-title" className="grid gap-6 border border-ink bg-paper p-6 lg:grid-cols-[1fr_1fr]">
      <div className="lg:col-span-2 flex items-center justify-between">
        <h2 id="pf-title" className="text-3xl">{isNew ? "New aircraft" : `Edit ${current?.name || "aircraft"}`}</h2>
        <button className="link" onClick={onCancel}>Close</button>
      </div>

      <form onSubmit={save} className="grid gap-4">
        <Field id="pf-name" label="Name" value={form.name} onChange={set("name")} required />
        <Field id="pf-maker" label="Manufacturer" value={form.manufacturer} onChange={set("manufacturer")} required />
        <div>
          <label className="field-label" htmlFor="pf-cat">Category</label>
          <select id="pf-cat" className="field" value={form.category} onChange={set("category")}>
            {CATEGORY_NAMES.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field id="pf-price" label="Price (US$, empty = on request)" type="number" min={0} value={form.price_usd} onChange={set("price_usd")} />
          {isNew && (
            <div>
              <label className="field-label" htmlFor="pf-status">Start as</label>
              <select id="pf-status" className="field" value={form.status} onChange={set("status")}>
                <option value="pending">Waiting for review</option>
                <option value="published">On the website</option>
              </select>
            </div>
          )}
        </div>
        <div>
          <label className="field-label" htmlFor="pf-desc">Description</label>
          <textarea id="pf-desc" rows={4} className="field" value={form.description} onChange={set("description")} />
        </div>
        <div>
          <label className="field-label" htmlFor="pf-specs">Specifications (JSON)</label>
          <textarea id="pf-specs" rows={6} className="field font-mono text-[0.9rem]" value={form.specs} onChange={set("specs")} />
          <p className="mt-1 text-[0.9rem] text-soft">Keys such as flight_time_min, max_range_km, max_speed_kmh, weight_kg, payload_kg.</p>
        </div>
        <Field id="pf-credit" label="Photo credit" value={form.image_credit} onChange={set("image_credit")} />
        <Field id="pf-source" label="Manufacturer page (https://…)" value={form.source_url} onChange={set("source_url")} />
        <div className="flex items-center gap-4">
          <button className="btn" disabled={state.status === "saving"}>{state.status === "saving" ? "Saving…" : isNew ? "Create aircraft" : "Save changes"}</button>
          <p aria-live="polite" className={`${state.status === "error" ? "text-route" : "text-soft"}`}>{state.message}</p>
        </div>
      </form>

      <div className="grid content-start gap-4">
        <h3 className="text-2xl">Photo</h3>
        {current?.image_url ? (
          <img src={current.image_url} alt={`${current.name}`} className="aspect-[4/3] w-full border border-rule object-cover" />
        ) : (
          <p className="text-soft">No photo yet. The site shows a drawing until you add one.</p>
        )}
        {isNew ? (
          <p className="text-soft">Save the aircraft first, then upload its photo.</p>
        ) : (
          <div>
            <label className="field-label" htmlFor="pf-photo">Upload a JPEG, PNG or WebP (2 MB max)</label>
            <input id="pf-photo" type="file" accept="image/jpeg,image/png,image/webp" onChange={uploadPhoto}
              disabled={photo.status === "uploading"} className="text-[0.95rem]" />
            <p aria-live="polite" className={`mt-2 ${photo.status === "error" ? "text-route" : "text-soft"}`}>
              {photo.status === "uploading" ? "Uploading…" : photo.message}
            </p>
          </div>
        )}
        {current && (
          <p className="text-[0.9rem] text-soft">
            Status: {current.status === "published" ? "on the website" : "waiting for review"}
            {current.manual_edit ? " · edited by hand, so scraper runs will not overwrite it" : ""}
          </p>
        )}
      </div>
    </section>
  );
}

function Field({ id, label, ...input }) {
  return (
    <div>
      <label className="field-label" htmlFor={id}>{label}</label>
      <input id={id} className="field" {...input} />
    </div>
  );
}

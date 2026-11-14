import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, useApi } from "../api.js";
import { useAuth } from "../auth.jsx";
import DroneCard from "../components/DroneCard.jsx";
import DroneImage from "../components/DroneImage.jsx";
import Page from "../components/Page.jsx";
import { ErrorNote, Loading } from "../components/Status.jsx";
import { formatPrice, specRows } from "../format.js";

export default function DroneDetail() {
  const { slug } = useParams();
  const drone = useApi(`/api/drones/${encodeURIComponent(slug)}`);
  const { session, token } = useAuth();

  if (drone.loading) return <Page><Loading what="aircraft" /></Page>;
  if (drone.error) {
    return (
      <Page title="Aircraft not found">
        <ErrorNote error={drone.error} retryHint="Check the link or browse the catalogue." />
        <Link to="/drones" className="link mt-6 inline-block font-display text-lg">Back to all aircraft</Link>
      </Page>
    );
  }

  const d = drone.data;
  return (
    <Page title={d.name}>
      <Link to="/drones" className="link font-display text-lg">← All aircraft</Link>

      <div className="mt-6 grid gap-10 lg:grid-cols-[1.25fr_1fr]">
        <figure>
          <div className="aspect-[4/3] overflow-hidden border border-rule bg-paper">
            <DroneImage drone={d} eager />
          </div>
          {d.image_credit && <figcaption className="mt-2 text-[0.9rem] text-soft">Photo: {d.image_credit}</figcaption>}
        </figure>

        <div>
          <p className="font-display text-lg font-medium text-route">{d.category}</p>
          <h1 className="mt-1 text-[clamp(2.75rem,5vw,4rem)]">{d.name}</h1>
          <p className="text-lg text-soft">{d.manufacturer}</p>
          <p className="tabular mt-4 font-display text-2xl">{formatPrice(d.price_usd)}</p>
          <p className="mt-5 max-w-measure text-lg">{d.description}</p>

          <div className="mt-6 flex flex-wrap gap-3">
            <SaveButton slug={d.slug} signedIn={session?.role === "customer"} token={token} />
            <a href={d.datasheet_url} className="btn-quiet">Download datasheet</a>
            {d.source_url && (
              <a href={d.source_url} className="btn-quiet" target="_blank" rel="noopener noreferrer">
                Manufacturer page
              </a>
            )}
          </div>
        </div>
      </div>

      <section className="mt-14" aria-labelledby="specs">
        <h2 id="specs" className="text-4xl">Specifications</h2>
        <dl className="mt-4 grid border-t border-rule md:grid-cols-2 md:gap-x-10">
          {specRows(d.specs).map((row) => (
            <div key={row.key} className="flex justify-between gap-4 border-b border-rule py-3">
              <dt className="font-display text-lg font-medium text-soft">{row.label}</dt>
              <dd className="tabular text-right">{row.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="mt-14 grid gap-10 md:grid-cols-[1fr_1fr]" aria-labelledby="quote">
        <div>
          <h2 id="quote" className="text-4xl">Request a quote</h2>
          <p className="mt-2 text-soft">Our sales team replies within two working days.</p>
          <QuoteForm slug={d.slug} />
        </div>
        {d.related?.length > 0 && (
          <div>
            <h2 className="text-4xl">Also in {d.category}</h2>
            <div className="mt-4 grid gap-5 sm:grid-cols-3 md:grid-cols-1">
              {d.related.map((r) => (
                <DroneCard key={r.slug} drone={r} />
              ))}
            </div>
          </div>
        )}
      </section>
    </Page>
  );
}

function SaveButton({ slug, signedIn, token }) {
  const [state, setState] = useState({ status: "idle", message: "" });

  if (!signedIn) {
    return <Link to="/account/login" className="btn-quiet">Sign in to save this aircraft</Link>;
  }

  async function save() {
    setState({ status: "saving", message: "" });
    try {
      await api(`/api/customers/me/favorites/${encodeURIComponent(slug)}`, { method: "POST", token });
      setState({ status: "saved", message: "Saved to your account." });
    } catch (error) {
      setState({ status: "error", message: error.detail });
    }
  }

  return (
    <span className="flex items-center gap-3">
      <button className="btn-quiet" onClick={save} disabled={state.status === "saving"}>Save to my account</button>
      <span aria-live="polite" className={state.status === "error" ? "text-route" : "text-soft"}>{state.message}</span>
    </span>
  );
}

function QuoteForm({ slug }) {
  const blank = { contact_name: "", email: "", company: "", quantity: 1, notes: "" };
  const [form, setForm] = useState(blank);
  const [state, setState] = useState({ status: "idle", message: "", ref: null });
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setState({ status: "sending", message: "", ref: null });
    try {
      const ref = await api("/api/quotes", {
        method: "POST",
        body: { ...form, quantity: Number(form.quantity) || 1, drone_slug: slug },
      });
      setState({ status: "done", message: "Thanks. Your quote request is in.", ref });
      setForm(blank);
    } catch (error) {
      setState({ status: "error", message: error.detail, ref: null });
    }
  }

  return (
    <form onSubmit={submit} className="mt-6 grid gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label className="field-label" htmlFor="q-name">Your name</label>
          <input id="q-name" className="field" required maxLength={80} value={form.contact_name} onChange={set("contact_name")} autoComplete="name" />
        </div>
        <div>
          <label className="field-label" htmlFor="q-email">Work email</label>
          <input id="q-email" type="email" className="field" required value={form.email} onChange={set("email")} autoComplete="email" />
        </div>
        <div>
          <label className="field-label" htmlFor="q-company">Company</label>
          <input id="q-company" className="field" value={form.company} onChange={set("company")} autoComplete="organization" />
        </div>
        <div>
          <label className="field-label" htmlFor="q-qty">Quantity</label>
          <input id="q-qty" type="number" min={1} max={10000} className="field" value={form.quantity} onChange={set("quantity")} />
        </div>
      </div>
      <div>
        <label className="field-label" htmlFor="q-notes">What will you use it for?</label>
        <textarea id="q-notes" rows={4} className="field" maxLength={1000} value={form.notes} onChange={set("notes")} />
      </div>
      <div>
        <button className="btn" disabled={state.status === "sending"}>
          {state.status === "sending" ? "Sending…" : "Send quote request"}
        </button>
      </div>
      <div aria-live="polite" className="min-h-[1.5rem]">
        {state.status === "error" && <p className="text-route">{state.message}</p>}
        {state.status === "done" && (
          <p className="text-ink">
            {state.message} Your reference is <strong>{state.ref.reference}</strong>.{" "}
            <Link className="link" to={`/quotes/${state.ref.id}?token=${encodeURIComponent(state.ref.token)}`}>
              View it
            </Link>
          </p>
        )}
      </div>
    </form>
  );
}

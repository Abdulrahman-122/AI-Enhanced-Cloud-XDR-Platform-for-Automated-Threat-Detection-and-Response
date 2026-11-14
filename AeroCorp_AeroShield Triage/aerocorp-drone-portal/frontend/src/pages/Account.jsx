import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useApi } from "../api.js";
import { useAuth } from "../auth.jsx";
import Page from "../components/Page.jsx";
import { Empty, ErrorNote, Loading } from "../components/Status.jsx";
import { formatDate, formatPrice } from "../format.js";

export default function Account() {
  const { session, token, login, logout } = useAuth();
  const isCustomer = session?.role === "customer";

  if (!isCustomer) {
    return (
      <Page title="Create an account">
        <div className="mx-auto max-w-xl">
          <SignUp onSession={login} />
          <p className="mt-6 text-lg">
            Already have an account?{" "}
            <Link to="/account/login" className="link font-display text-xl">Sign in</Link>
          </p>
        </div>
      </Page>
    );
  }

  return (
    <Page title="My account">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[clamp(2.5rem,5vw,4rem)]">Welcome, {session.name}</h1>
          <p className="mt-2 text-soft">{session.email}{session.company ? ` · ${session.company}` : ""}</p>
        </div>
        <button className="btn-quiet" onClick={logout}>Sign out</button>
      </div>

      <div className="mt-10 grid gap-12 lg:grid-cols-[1fr_1.4fr]">
        <div className="grid content-start gap-12">
          <ProfileForm token={token} onSaved={login} session={session} />
          <Favourites token={token} />
        </div>
        <QuoteList token={token} />
      </div>
    </Page>
  );
}

function SignUp({ onSession }) {
  const blank = { name: "", email: "", company: "", password: "" };
  const [form, setForm] = useState(blank);
  const [state, setState] = useState({ busy: false, error: "" });
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setState({ busy: true, error: "" });
    try {
      const result = await api("/api/customers/register", { method: "POST", body: form });
      onSession({ ...result, role: "customer" });
    } catch (error) {
      setState({ busy: false, error: error.detail });
    }
  }

  return (
    <section aria-labelledby="register-title">
      <h2 id="register-title" className="text-4xl">Create an account</h2>
      <p className="mt-2 text-soft">Save aircraft, keep track of your quote requests and get the newsletter.</p>
      <form onSubmit={submit} className="mt-6 grid gap-4 border border-rule bg-paper p-6">
        <div>
          <label className="field-label" htmlFor="r-name">Your name</label>
          <input id="r-name" className="field" required maxLength={80} autoComplete="name" value={form.name} onChange={set("name")} />
        </div>
        <div>
          <label className="field-label" htmlFor="r-email">Email</label>
          <input id="r-email" type="email" className="field" required autoComplete="email" value={form.email} onChange={set("email")} />
        </div>
        <div>
          <label className="field-label" htmlFor="r-company">Company (optional)</label>
          <input id="r-company" className="field" maxLength={120} autoComplete="organization" value={form.company} onChange={set("company")} />
        </div>
        <div>
          <label className="field-label" htmlFor="r-pass">Password</label>
          <input id="r-pass" type="password" className="field" required autoComplete="new-password" value={form.password} onChange={set("password")} />
          <p className="mt-1 text-[0.9rem] text-soft">At least 8 characters.</p>
        </div>
        <button className="btn" disabled={state.busy}>{state.busy ? "Creating account…" : "Create account"}</button>
        <p aria-live="polite" className="min-h-[1.5rem] text-route">{state.error}</p>
      </form>
    </section>
  );
}

function ProfileForm({ token, session, onSaved }) {
  const [form, setForm] = useState({ name: session.name || "", company: session.company || "" });
  const [state, setState] = useState({ status: "idle", message: "" });
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setState({ status: "saving", message: "" });
    try {
      const profile = await api("/api/customers/me", { method: "PUT", token, body: form });
      onSaved({ ...session, name: profile.name, company: profile.company });
      setState({ status: "saved", message: "Profile saved." });
    } catch (error) {
      setState({ status: "error", message: error.detail });
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-4 border border-rule bg-paper p-6">
      <h2 className="text-3xl">Your details</h2>
      <div>
        <label className="field-label" htmlFor="p-name">Name</label>
        <input id="p-name" className="field" required maxLength={80} value={form.name} onChange={set("name")} />
      </div>
      <div>
        <label className="field-label" htmlFor="p-company">Company</label>
        <input id="p-company" className="field" maxLength={120} value={form.company} onChange={set("company")} />
      </div>
      <div>
        <button className="btn-quiet" disabled={state.status === "saving"}>Save details</button>
      </div>
      <p aria-live="polite" className={`min-h-[1.5rem] ${state.status === "error" ? "text-route" : "text-soft"}`}>{state.message}</p>
    </form>
  );
}

function Favourites({ token }) {
  const [reload, setReload] = useState(0);
  const favs = useApi("/api/customers/me/favorites", { token, reload });

  async function remove(slug) {
    await api(`/api/customers/me/favorites/${encodeURIComponent(slug)}`, { method: "DELETE", token });
    setReload((n) => n + 1);
  }

  return (
    <section aria-labelledby="favs-title">
      <h2 id="favs-title" className="text-3xl">Saved aircraft</h2>
      {favs.loading && <Loading what="saved aircraft" />}
      {favs.error && <ErrorNote error={favs.error} />}
      {favs.data && favs.data.length === 0 && (
        <Empty title="Nothing saved yet">Use “Save to my account” on any aircraft page.</Empty>
      )}
      {favs.data?.length > 0 && (
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {favs.data.map((f) => (
            <li key={f.slug} className="flex items-center justify-between gap-4 py-3">
              <div>
                <Link to={`/drones/${f.slug}`} className="link font-display text-lg">{f.name}</Link>
                <p className="text-[0.9rem] text-soft">{f.manufacturer} · {formatPrice(f.price_usd)}</p>
              </div>
              <button className="link text-[0.95rem]" onClick={() => remove(f.slug)}>Remove</button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function QuoteList({ token }) {
  const quotes = useApi("/api/customers/me/quotes", { token });

  return (
    <section aria-labelledby="quotes-title">
      <h2 id="quotes-title" className="text-3xl">Your quote requests</h2>
      {quotes.loading && <Loading what="quote requests" />}
      {quotes.error && <ErrorNote error={quotes.error} />}
      {quotes.data && quotes.data.length === 0 && (
        <Empty title="No quote requests yet">Requests you send while signed in appear here.</Empty>
      )}
      {quotes.data?.length > 0 && (
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {quotes.data.map((q) => (
            <li key={q.id} className="flex flex-wrap justify-between gap-2 py-4">
              <div>
                <p className="font-display text-lg">{q.reference} · {q.drone_name || q.drone_slug}</p>
                <p className="text-soft">Quantity {q.quantity}</p>
              </div>
              <p className="text-soft">{formatDate(q.created_at)}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

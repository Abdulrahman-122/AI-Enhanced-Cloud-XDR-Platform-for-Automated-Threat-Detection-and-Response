import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import Page from "../components/Page.jsx";

export default function AccountLogin() {
  const { session, login } = useAuth();
  if (session?.role === "customer") return <Navigate to="/account" replace />;

  return (
    <Page title="Sign in">
      <SignIn onSession={login} />
    </Page>
  );
}

function SignIn({ onSession }) {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [state, setState] = useState({ busy: false, error: "" });
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setState({ busy: true, error: "" });
    try {
      const result = await api("/api/customers/login", { method: "POST", body: form });
      onSession(result);
      navigate("/account");
    } catch (error) {
      setState({ busy: false, error: error.detail });
    }
  }

  return (
    <section aria-labelledby="signin-title" className="mx-auto max-w-md">
      <h2 id="signin-title" className="text-4xl">Sign in</h2>
      <p className="mt-2 text-soft">Staff use the staff sign-in in the footer.</p>
      <form onSubmit={submit} className="mt-6 grid gap-4 border border-rule bg-paper p-6">
        <div>
          <label className="field-label" htmlFor="s-email">Email</label>
          <input id="s-email" type="email" className="field" required autoComplete="email" value={form.email} onChange={set("email")} />
        </div>
        <div>
          <label className="field-label" htmlFor="s-pass">Password</label>
          <input id="s-pass" type="password" className="field" required autoComplete="current-password" value={form.password} onChange={set("password")} />
        </div>
        <button className="btn" disabled={state.busy}>{state.busy ? "Signing in…" : "Sign in"}</button>
        <p aria-live="polite" className="min-h-[1.5rem] text-route">{state.error}</p>
      </form>
      <p className="mt-6 text-lg">
        New here?{" "}
        <Link to="/account" className="link font-display text-xl">Create an account</Link>
      </p>
    </section>
  );
}


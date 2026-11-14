import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useAuth } from "../auth.jsx";
import Page from "../components/Page.jsx";

export default function Login() {
  const { session, login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", password: "" });
  const [state, setState] = useState({ busy: false, error: "" });
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setState({ busy: true, error: "" });
    try {
      const result = await api("/api/auth/login", { method: "POST", body: form });
      login(result);
      navigate("/admin");
    } catch (error) {
      setState({ busy: false, error: error.detail });
    }
  }

  // Only a staff session counts here. A customer signed in on this browser sees the form.
  if (session?.role === "admin" || session?.role === "sales") {
    return (
      <Page title="Staff sign-in">
        <p className="text-lg">You are signed in as <strong>{session.username}</strong>.</p>
        <Link to="/admin" className="link mt-4 inline-block font-display text-lg">Go to the staff inbox</Link>
      </Page>
    );
  }

  return (
    <Page title="Staff sign-in">
      <div className="mx-auto max-w-md">
        <h1 className="text-[clamp(2.5rem,5vw,3.5rem)]">Staff sign-in</h1>
        <p className="mt-3 text-soft">For AeroCorp staff only. Customers sign in on the My account page.</p>
        <form onSubmit={submit} className="mt-8 grid gap-4 border border-rule bg-paper p-6">
          <div>
            <label className="field-label" htmlFor="l-user">Username</label>
            <input id="l-user" className="field" required autoComplete="username" value={form.username} onChange={set("username")} />
          </div>
          <div>
            <label className="field-label" htmlFor="l-pass">Password</label>
            <input id="l-pass" type="password" className="field" required autoComplete="current-password" value={form.password} onChange={set("password")} />
          </div>
          <button className="btn" disabled={state.busy}>{state.busy ? "Signing in…" : "Sign in"}</button>
          <p aria-live="polite" className="min-h-[1.5rem] text-route">{state.error}</p>
        </form>
      </div>
    </Page>
  );
}

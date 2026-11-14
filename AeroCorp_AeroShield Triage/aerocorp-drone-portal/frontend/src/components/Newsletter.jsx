import { useState } from "react";
import { api } from "../api.js";

export default function Newsletter() {
  const [email, setEmail] = useState("");
  const [state, setState] = useState({ status: "idle", message: "" });

  async function submit(event) {
    event.preventDefault();
    setState({ status: "sending", message: "" });
    try {
      const result = await api("/api/newsletter", { method: "POST", body: { email } });
      setState({ status: "done", message: result?.message || "You're on the list." });
      setEmail("");
    } catch (error) {
      setState({ status: "error", message: error.detail });
    }
  }

  return (
    <form onSubmit={submit} aria-labelledby="newsletter-title">
      <h2 id="newsletter-title" className="text-3xl">Field notes</h2>
      <p className="mt-1 max-w-sm text-soft">One email a month: new aircraft, training days and operator guides.</p>
      <div className="mt-4 flex max-w-md flex-col gap-2 sm:flex-row">
        <div className="flex-1">
          <label htmlFor="newsletter-email" className="sr-only">Email address</label>
          <input
            id="newsletter-email"
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="you@company.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="field"
          />
        </div>
        <button className="btn" disabled={state.status === "sending"}>
          {state.status === "sending" ? "Subscribing…" : "Subscribe"}
        </button>
      </div>
      <p aria-live="polite" className={`mt-2 min-h-[1.65rem] text-[0.95rem] ${state.status === "error" ? "text-route" : "text-soft"}`}>
        {state.message}
      </p>
    </form>
  );
}

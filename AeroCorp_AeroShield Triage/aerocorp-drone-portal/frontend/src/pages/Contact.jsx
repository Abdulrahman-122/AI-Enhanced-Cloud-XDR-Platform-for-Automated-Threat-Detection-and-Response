import { useState } from "react";
import { api } from "../api.js";
import Page from "../components/Page.jsx";

const blank = { name: "", email: "", subject: "", message: "", website: "" };

export default function Contact() {
  const [form, setForm] = useState(blank);
  const [state, setState] = useState({ status: "idle", message: "" });
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setState({ status: "sending", message: "" });
    try {
      await api("/api/contact", { method: "POST", body: form });
      setState({ status: "done", message: "Thanks. A member of the team will reply within two working days." });
      setForm(blank);
    } catch (error) {
      setState({ status: "error", message: error.detail });
    }
  }

  return (
    <Page title="Contact">
      <div className="grid gap-12 md:grid-cols-[1fr_1.2fr]">
        <div>
          <h1 className="text-[clamp(2.75rem,6vw,4.5rem)]">Contact us</h1>
          <p className="mt-4 max-w-measure text-lg text-soft">
            Questions about aircraft, training or support? Send a message and we will route it to the right team.
          </p>
          <dl className="mt-8 space-y-4 text-lg">
            <div>
              <dt className="font-display text-xl font-medium">Sales</dt>
              <dd className="text-soft">sales@aerocorp.example</dd>
            </div>
            <div>
              <dt className="font-display text-xl font-medium">Support</dt>
              <dd className="text-soft">support@aerocorp.example</dd>
            </div>
          </dl>
        </div>

        <form onSubmit={submit} className="grid gap-4 border border-rule bg-paper p-6 md:p-8" noValidate={false}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="field-label" htmlFor="c-name">Name</label>
              <input id="c-name" className="field" required value={form.name} onChange={set("name")} autoComplete="name" />
            </div>
            <div>
              <label className="field-label" htmlFor="c-email">Email</label>
              <input id="c-email" type="email" className="field" required value={form.email} onChange={set("email")} autoComplete="email" />
            </div>
          </div>
          <div>
            <label className="field-label" htmlFor="c-subject">Subject</label>
            <input id="c-subject" className="field" value={form.subject} onChange={set("subject")} />
          </div>
          <div>
            <label className="field-label" htmlFor="c-message">Message</label>
            <textarea id="c-message" rows={6} className="field" required minLength={5} value={form.message} onChange={set("message")} />
          </div>

          {/* Honeypot: hidden from people, but simple bots fill every field they find. */}
          <div className="absolute -left-[10000px] h-0 overflow-hidden" aria-hidden="true">
            <label htmlFor="c-website">Leave this field empty</label>
            <input id="c-website" tabIndex={-1} autoComplete="off" value={form.website} onChange={set("website")} />
          </div>

          <div>
            <button className="btn" disabled={state.status === "sending"}>
              {state.status === "sending" ? "Sending…" : "Send message"}
            </button>
          </div>
          <p aria-live="polite" className={`min-h-[1.5rem] ${state.status === "error" ? "text-route" : "text-ink"}`}>
            {state.message}
          </p>
        </form>
      </div>
    </Page>
  );
}

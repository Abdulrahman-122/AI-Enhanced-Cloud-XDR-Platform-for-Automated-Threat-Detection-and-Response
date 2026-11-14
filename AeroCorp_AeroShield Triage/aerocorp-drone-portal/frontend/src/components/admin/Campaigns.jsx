import { useState } from "react";
import { api, useApi } from "../../api.js";
import { formatDate } from "../../format.js";
import { Empty, ErrorNote, Loading } from "../Status.jsx";

/**
 * Newsletter editor. Admin and sales staff write drafts; only an admin can send.
 * The body is plain text: line breaks are kept, and HTML is never rendered in the newsletter preview.
 */
export default function Campaigns({ token, role }) {
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState(null); // campaign id, "new", or null
  const [notice, setNotice] = useState(""); // success messages survive the editor remounting after a first save
  const list = useApi("/api/admin/campaigns", { token, reload });
  const refresh = () => setReload((n) => n + 1);
  const canSend = role === "admin";

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_1.5fr]">
      <div className="grid content-start gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl">Newsletters</h2>
          <button className="btn" onClick={() => { setNotice(""); setSelected("new"); }}>New newsletter</button>
        </div>
        {list.loading && <Loading what="newsletters" />}
        {list.error && <ErrorNote error={list.error} />}
        {list.data && list.data.length === 0 && (
          <Empty title="No newsletters yet">Write one, and an admin can send it to subscribers.</Empty>
        )}
        <ul className="divide-y divide-rule border-y border-rule">
          {(list.data || []).map((c) => (
            <li key={c.id}>
              <button onClick={() => { setNotice(""); setSelected(c.id); }} aria-current={selected === c.id}
                className={`flex w-full flex-col gap-1 py-3 text-left ${selected === c.id ? "text-route" : ""}`}>
                <span className="font-display text-lg">{c.subject}</span>
                <span className="text-[0.9rem] text-soft">
                  {c.status === "sent" ? `Sent ${formatDate(c.sent_at)} to ${c.recipients}` : "Draft"} · {c.author}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <p aria-live="polite" className="mb-3 min-h-[1.5rem] text-soft">{notice}</p>
        {selected ? (
          <Editor
            key={selected}
            id={selected === "new" ? null : selected}
            token={token}
            canSend={canSend}
            onChanged={(id, message) => { refresh(); setSelected(id); setNotice(message); }}
            campaign={list.data?.find((c) => c.id === selected)}
          />
        ) : (
          <Empty title="Choose a newsletter">Pick one from the list, or start a new one.</Empty>
        )}
      </div>
    </div>
  );
}

function Editor({ id, token, canSend, campaign, onChanged }) {
  const isNew = id === null;
  const [form, setForm] = useState({ subject: campaign?.subject || "", body: campaign?.body || "" });
  const [state, setState] = useState({ status: "idle", message: "" });
  const sent = campaign?.status === "sent";
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function save(event) {
    event?.preventDefault();
    setState({ status: "saving", message: "" });
    try {
      const saved = isNew
        ? await api("/api/admin/campaigns", { method: "POST", token, body: form })
        : await api(`/api/admin/campaigns/${id}`, { method: "PUT", token, body: form });
      onChanged(saved.id, "Draft saved.");
    } catch (err) {
      setState({ status: "error", message: err.detail });
    }
  }

  async function send() {
    if (!window.confirm(`Send “${form.subject}” to all subscribers? This cannot be undone.`)) return;
    setState({ status: "saving", message: "" });
    try {
      const result = await api(`/api/admin/campaigns/${id}/send`, { method: "POST", token });
      onChanged(id, `Sent to ${result.recipients} subscriber(s).`);
    } catch (err) {
      setState({ status: "error", message: err.detail });
    }
  }

  return (
    <div className="grid gap-6">
      <form onSubmit={save} className="grid gap-4 border border-rule bg-paper p-6">
        <div>
          <label className="field-label" htmlFor="c-subject">Subject</label>
          <input id="c-subject" className="field" required maxLength={200} value={form.subject} onChange={set("subject")} disabled={sent} />
        </div>
        <div>
          <label className="field-label" htmlFor="c-body">Message (plain text; blank lines start a new paragraph)</label>
          <textarea id="c-body" rows={12} className="field font-body" required maxLength={50000} value={form.body} onChange={set("body")} disabled={sent} />
        </div>
        <div className="flex flex-wrap items-center gap-4">
          {!sent && <button className="btn" disabled={state.status === "saving"}>Save draft</button>}
          {!sent && canSend && !isNew && (
            <button type="button" className="btn-quiet" onClick={send} disabled={state.status === "saving"}>Send to subscribers</button>
          )}
          {!sent && !canSend && !isNew && <p className="text-soft">Only an admin can send a newsletter.</p>}
          {sent && <p className="text-soft">Sent on {formatDate(campaign.sent_at)} to {campaign.recipients} subscriber(s).</p>}
        </div>
        {state.status === "error" && <p role="alert" className="text-route">{state.message}</p>}
      </form>

      <section aria-labelledby="c-preview" className="border border-dashed border-rule p-6">
        <h3 id="c-preview" className="text-2xl">Preview</h3>
        <p className="mt-3 font-display text-2xl font-semibold">{form.subject || "Untitled newsletter"}</p>
        <div className="mt-3 whitespace-pre-wrap text-lg">{form.body}</div>
      </section>
    </div>
  );
}

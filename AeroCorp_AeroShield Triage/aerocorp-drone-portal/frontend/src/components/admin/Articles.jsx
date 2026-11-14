import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useApi } from "../../api.js";
import { formatDate } from "../../format.js";
import { Empty, ErrorNote, Loading } from "../Status.jsx";
import { ARTICLE_CATEGORIES } from "./categories.js";

/**
 * News and guides editor. Admin and sales staff write articles as drafts. Only an admin publishes,
 * takes down or deletes one, and only an admin can change an article after it is published.
 */
export default function Articles({ token, role }) {
  const [reload, setReload] = useState(0);
  const [selected, setSelected] = useState(null); // article id, "new", or null
  const [notice, setNotice] = useState("");
  const list = useApi("/api/admin/articles", { token, reload });
  const isAdmin = role === "admin";
  const refresh = () => setReload((n) => n + 1);

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_1.5fr]">
      <div className="grid content-start gap-4">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl">News and guides</h2>
          <button className="btn" onClick={() => { setNotice(""); setSelected("new"); }}>New article</button>
        </div>
        {list.loading && <Loading what="articles" />}
        {list.error && <ErrorNote error={list.error} />}
        {list.data && list.data.length === 0 && <Empty title="No articles">Write the first one.</Empty>}
        <ul className="divide-y divide-rule border-y border-rule">
          {(list.data || []).map((a) => (
            <li key={a.id}>
              <button onClick={() => { setNotice(""); setSelected(a.id); }} aria-current={selected === a.id}
                className={`flex w-full flex-col gap-1 py-3 text-left ${selected === a.id ? "text-route" : ""}`}>
                <span className="font-display text-lg">{a.title}</span>
                <span className="text-[0.9rem] text-soft">
                  {a.status === "published" ? "On the News page" : "Draft"} · {a.category} · {a.author}
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
            isAdmin={isAdmin}
            article={list.data?.find((a) => a.id === selected)}
            onChanged={(id, message) => { refresh(); setSelected(id); setNotice(message); }}
            onDeleted={() => { refresh(); setSelected(null); setNotice("Article deleted."); }}
          />
        ) : (
          <Empty title="Choose an article">Pick one from the list, or start a new one.</Empty>
        )}
      </div>
    </div>
  );
}

function Editor({ id, token, isAdmin, article, onChanged, onDeleted }) {
  const isNew = id === null;
  const [form, setForm] = useState({
    title: article?.title || "", summary: article?.summary || "",
    category: article?.category || ARTICLE_CATEGORIES[0], body: article?.body || "",
  });
  const [state, setState] = useState({ status: "idle", message: "" });
  const published = article?.status === "published";
  const locked = published && !isAdmin;
  const set = (key) => (event) => setForm((f) => ({ ...f, [key]: event.target.value }));

  async function save(event) {
    event?.preventDefault();
    setState({ status: "saving", message: "" });
    try {
      const saved = isNew
        ? await api("/api/admin/articles", { method: "POST", token, body: form })
        : await api(`/api/admin/articles/${id}`, { method: "PUT", token, body: form });
      onChanged(saved.id, "Saved.");
    } catch (err) {
      setState({ status: "error", message: err.detail });
    }
  }

  async function setStatus(status) {
    if (status === "published" && !window.confirm(`Publish “${form.title}” on the News page?`)) return;
    setState({ status: "saving", message: "" });
    try {
      const saved = await api(`/api/admin/articles/${id}/status`, { method: "POST", token, body: { status } });
      onChanged(saved.id, status === "published" ? "Published." : "Taken down. It is a draft again.");
    } catch (err) {
      setState({ status: "error", message: err.detail });
    }
  }

  async function remove() {
    if (!window.confirm(`Delete “${form.title}” permanently?`)) return;
    try {
      await api(`/api/admin/articles/${id}`, { method: "DELETE", token });
      onDeleted();
    } catch (err) {
      setState({ status: "error", message: err.detail });
    }
  }

  return (
    <div className="grid gap-6">
      <form onSubmit={save} className="grid gap-4 border border-rule bg-paper p-6">
        <div>
          <label className="field-label" htmlFor="a-title">Title</label>
          <input id="a-title" className="field" required maxLength={200} value={form.title} onChange={set("title")} disabled={locked} />
        </div>
        <div className="grid gap-4 sm:grid-cols-[1fr_1fr]">
          <div>
            <label className="field-label" htmlFor="a-cat">Category</label>
            <select id="a-cat" className="field" value={form.category} onChange={set("category")} disabled={locked}>
              {ARTICLE_CATEGORIES.map((c) => <option key={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <label className="field-label" htmlFor="a-sum">Short summary</label>
            <input id="a-sum" className="field" maxLength={500} value={form.summary} onChange={set("summary")} disabled={locked} />
          </div>
        </div>
        <div>
          <label className="field-label" htmlFor="a-body">Article (blank lines start a new paragraph)</label>
          <textarea id="a-body" rows={14} className="field font-body" maxLength={50000} value={form.body} onChange={set("body")} disabled={locked} />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          {!locked && <button className="btn" disabled={state.status === "saving"}>{isNew ? "Save draft" : "Save changes"}</button>}
          {!isNew && isAdmin && !published && (
            <button type="button" className="btn-quiet" onClick={() => setStatus("published")} disabled={state.status === "saving"}>Publish</button>
          )}
          {!isNew && isAdmin && published && (
            <button type="button" className="btn-quiet" onClick={() => setStatus("draft")} disabled={state.status === "saving"}>Take down</button>
          )}
          {!isNew && isAdmin && (
            <button type="button" className="link text-route" onClick={remove}>Delete</button>
          )}
          {!isNew && published && (
            <Link to={`/news/${article.slug}`} className="link">View on the site</Link>
          )}
        </div>
        {locked && <p className="text-soft">This article is on the site. Only an admin can change it.</p>}
        {state.status === "error" && <p role="alert" className="text-route">{state.message}</p>}
      </form>
    </div>
  );
}

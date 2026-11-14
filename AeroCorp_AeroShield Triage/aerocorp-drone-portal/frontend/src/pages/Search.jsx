import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useApi } from "../api.js";
import DroneCard from "../components/DroneCard.jsx";
import Html from "../components/Html.jsx";
import Page from "../components/Page.jsx";
import { Empty, ErrorNote, Loading } from "../components/Status.jsx";
import { formatDate } from "../format.js";

export default function Search() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const category = params.get("category") || "";
  const [term, setTerm] = useState(q);

  useEffect(() => setTerm(q), [q]);

  const categories = useApi("/api/categories");
  const query = new URLSearchParams({ q });
  if (category) query.set("category", category);
  const result = useApi(q.trim() ? `/api/search?${query}` : null);

  function submit(event) {
    event.preventDefault();
    const next = new URLSearchParams();
    if (term.trim()) next.set("q", term.trim());
    if (category) next.set("category", category);
    setParams(next);
  }

  function setCategory(value) {
    const next = new URLSearchParams(params);
    if (value) next.set("category", value);
    else next.delete("category");
    setParams(next);
  }

  const d = result.data;
  const title = q ? `Search: ${q}` : "Search";

  return (
    <Page title={title}>
      <h1 className="text-[clamp(2.75rem,6vw,4.5rem)]">Search</h1>

      <form onSubmit={submit} role="search" className="mt-6 grid gap-3 md:grid-cols-[1fr_15rem_auto]">
        <div>
          <label htmlFor="search-term" className="sr-only">Search text</label>
          <input
            id="search-term"
            type="search"
            className="field"
            placeholder="Try a name, manufacturer or use case"
            value={term}
            onChange={(e) => setTerm(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="search-category" className="sr-only">Class</label>
          <select id="search-category" className="field" value={category} onChange={(e) => setCategory(e.target.value)}>
            <option value="">All classes</option>
            {(categories.data || []).map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <button className="btn">Search</button>
      </form>

      <div className="mt-10" aria-live="polite">
        {!q.trim() && <Empty title="Search the catalogue and news">Type a name such as “mapping”, “Skydio” or “spray”.</Empty>}

        {q.trim() && result.loading && <Loading what="results" />}

        {q.trim() && result.error && (
          <>
            <ErrorNote error={result.error} retryHint="Check your search and try again." />
            {/* Verbose database errors are part of the lab build. The hardened build never sends these fields. */}
            {result.error.data?.query && (
              <pre className="mt-4 overflow-x-auto border border-rule bg-paper p-4 text-sm">{result.error.data.query}</pre>
            )}
          </>
        )}

        {d && (
          <>
            <p className="text-lg">
              {d.count} {d.count === 1 ? "result" : "results"} for “<Html value={d.query_display} />”
            </p>

            {d.drones.length > 0 && (
              <section className="mt-8" aria-labelledby="drone-results">
                <h2 id="drone-results" className="text-3xl">Aircraft</h2>
                <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                  {d.drones.map((drone, i) => (
                    <DroneCard key={drone.slug ?? i} drone={drone} showCategory />
                  ))}
                </div>
              </section>
            )}

            {d.posts.length > 0 && (
              <section className="mt-10" aria-labelledby="post-results">
                <h2 id="post-results" className="text-3xl">News and guides</h2>
                <ul className="mt-4 divide-y divide-rule border-y border-rule">
                  {d.posts.map((post) => (
                    <li key={post.slug} className="py-4">
                      <p className="font-display text-base text-route">{formatDate(post.published_at)}</p>
                      <Link to={`/news/${encodeURIComponent(post.slug)}`} className="text-2xl hover:text-route">
                        {post.title}
                      </Link>
                      <p className="text-soft">{post.summary}</p>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {d.count === 0 && <Empty title="Nothing matched">Try a shorter word or pick “All classes”.</Empty>}
          </>
        )}
      </div>
    </Page>
  );
}

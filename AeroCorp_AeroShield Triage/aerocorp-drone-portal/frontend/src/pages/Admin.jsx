import { useState } from "react";
import { Link } from "react-router-dom";
import { useApi } from "../api.js";
import { useAuth } from "../auth.jsx";
import Articles from "../components/admin/Articles.jsx";
import Campaigns from "../components/admin/Campaigns.jsx";
import Products from "../components/admin/Products.jsx";
import Html from "../components/Html.jsx";
import Page from "../components/Page.jsx";
import { Empty, ErrorNote, Loading } from "../components/Status.jsx";
import { formatDate } from "../format.js";

// Tabs that only read a list from the API. "products" and "campaigns" have their own components.
const READ_TABS = new Set(["stats", "messages", "quotes", "subscribers"]);
const TABS = [
  ["stats", "Overview", ["admin", "sales"]],
  ["messages", "Contact inbox", ["admin", "sales"]],
  ["quotes", "Quote requests", ["admin", "sales"]],
  ["subscribers", "Subscribers", ["admin", "sales"]],
  ["articles", "News articles", ["admin", "sales"]],
  ["campaigns", "Newsletters", ["admin", "sales"]],
  ["products", "Aircraft", ["admin"]],
];

export default function Admin() {
  const { session, token } = useAuth();
  const [tab, setTab] = useState("stats");
  const isStaff = session?.role === "admin" || session?.role === "sales";
  const visibleTabs = TABS.filter(([, , roles]) => roles.includes(session?.role));
  const data = useApi(isStaff && READ_TABS.has(tab) ? `/api/admin/${tab}` : null, { token });

  if (!isStaff) {
    return (
      <Page title="Staff inbox">
        <Empty title="Staff sign-in required">
          <Link to="/login" className="link">Sign in with a staff account to view the inbox.</Link>
        </Empty>
      </Page>
    );
  }

  return (
    <Page title="Staff inbox">
      <h1 className="text-[clamp(2.5rem,5vw,4rem)]">Staff inbox</h1>
      <p className="mt-2 text-soft">Signed in as {session.username} ({session.role}).</p>

      <div role="tablist" aria-label="Staff sections" className="mt-6 flex flex-wrap gap-2">
        {visibleTabs.map(([key, label]) => (
          <button
            key={key}
            role="tab"
            aria-selected={tab === key}
            onClick={() => setTab(key)}
            className={`border px-4 py-2 font-display text-lg font-medium ${
              tab === key ? "border-ink bg-ink text-chart" : "border-rule bg-paper hover:border-ink"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="mt-8">
        {tab === "products" && <Products token={token} />}
        {tab === "articles" && <Articles token={token} role={session.role} />}
        {tab === "campaigns" && <Campaigns token={token} role={session.role} />}
        {READ_TABS.has(tab) && data.loading && <Loading what="inbox" />}
        {READ_TABS.has(tab) && data.error && (
          <ErrorNote
            error={data.error}
            retryHint={data.error.status === 401 ? "Your session may have expired. Sign in again." : "Try again in a moment."}
          />
        )}
        {READ_TABS.has(tab) && data.data && tab === "stats" && <Stats stats={data.data} />}
        {READ_TABS.has(tab) && data.data && tab === "messages" && <Messages rows={data.data} />}
        {READ_TABS.has(tab) && data.data && tab === "quotes" && <Quotes rows={data.data} />}
        {READ_TABS.has(tab) && data.data && tab === "subscribers" && <Subscribers rows={data.data} />}
      </div>
    </Page>
  );
}

function Stats({ stats }) {
  return (
    <dl className="grid gap-4 sm:grid-cols-3">
      {Object.entries(stats).map(([key, value]) => (
        <div key={key} className="border border-rule bg-paper p-5">
          <dt className="font-display text-lg font-medium capitalize text-soft">{key}</dt>
          <dd className="tabular mt-1 font-display text-5xl font-semibold">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Messages({ rows }) {
  if (rows.length === 0) return <Empty title="No messages yet">Contact form submissions appear here.</Empty>;
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {rows.map((m) => (
        <li key={m.id} className="py-5">
          <p className="font-display text-lg">
            <Html value={m.subject_html} as="strong" /> <span className="text-soft">from <Html value={m.name_html} /> &lt;<Html value={m.email_html} />&gt;</span>
          </p>
          <p className="text-[0.9rem] text-soft">{formatDate(m.created_at)} · IP {m.ip}</p>
          <Html value={m.message_html} as="p" className="mt-2 whitespace-pre-wrap text-lg" />
        </li>
      ))}
    </ul>
  );
}

function Quotes({ rows }) {
  if (rows.length === 0) return <Empty title="No quote requests yet">Requests from aircraft pages appear here.</Empty>;
  return (
    <div className="overflow-x-auto border border-rule bg-paper">
      <table className="w-full min-w-[40rem] text-left">
        <thead className="border-b border-rule font-display text-lg text-soft">
          <tr>
            <th className="p-3">Reference</th>
            <th className="p-3">Aircraft</th>
            <th className="p-3">Contact</th>
            <th className="p-3">Qty</th>
            <th className="p-3">Received</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((q) => (
            <tr key={q.id} className="border-b border-rule last:border-0">
              <td className="p-3 font-display text-lg">{q.reference}</td>
              <td className="p-3">{q.drone_slug}</td>
              <td className="p-3">
                <Html value={q.contact_name} /> · <Html value={q.email} /> · <Html value={q.company} />
              </td>
              <td className="tabular p-3">{q.quantity}</td>
              <td className="p-3 text-soft">{formatDate(q.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Subscribers({ rows }) {
  if (rows.length === 0) return <Empty title="No subscribers yet">Newsletter sign-ups appear here.</Empty>;
  return (
    <ul className="divide-y divide-rule border-y border-rule">
      {rows.map((s) => (
        <li key={s.id} className="flex justify-between gap-4 py-3">
          <span>{s.email}</span>
          <span className="text-soft">{formatDate(s.created_at)}</span>
        </li>
      ))}
    </ul>
  );
}

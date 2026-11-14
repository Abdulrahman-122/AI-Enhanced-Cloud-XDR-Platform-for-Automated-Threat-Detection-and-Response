import { Link, useParams, useSearchParams } from "react-router-dom";
import { useApi } from "../api.js";
import Html from "../components/Html.jsx";
import Page from "../components/Page.jsx";
import { ErrorNote, Loading } from "../components/Status.jsx";

export default function QuoteView() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const quote = useApi(`/api/quotes/${encodeURIComponent(id)}?token=${encodeURIComponent(token)}`);

  if (quote.loading) return <Page><Loading what="quote" /></Page>;
  if (quote.error) {
    return (
      <Page title="Quote not found">
        <ErrorNote error={quote.error} retryHint="Check the link from your confirmation." />
        <Link to="/drones" className="link mt-6 inline-block font-display text-lg">Browse aircraft</Link>
      </Page>
    );
  }

  const q = quote.data;
  return (
    <Page title={`Quote ${q.reference}`}>
      <p className="font-display text-lg font-medium text-route">Quote request</p>
      <h1 className="mt-1 text-[clamp(2.5rem,5vw,4rem)]">{q.reference}</h1>
      <dl className="mt-8 grid max-w-2xl gap-x-8 border-t border-rule md:grid-cols-2">
        <Row label="Aircraft">
          {q.drone_name ? <Link className="link" to={`/drones/${encodeURIComponent(q.drone_slug)}`}>{q.drone_name}</Link> : q.drone_slug}
        </Row>
        <Row label="Quantity">{q.quantity}</Row>
        <Row label="Name"><Html value={q.contact_name} /></Row>
        <Row label="Email"><Html value={q.email} /></Row>
        <Row label="Company"><Html value={q.company} /></Row>
        <Row label="Submitted">{new Date(q.created_at).toLocaleString("en-GB")}</Row>
        <div className="md:col-span-2">
          <Row label="Notes"><Html value={q.notes} as="p" className="whitespace-pre-wrap" /></Row>
        </div>
      </dl>
    </Page>
  );
}

function Row({ label, children }) {
  return (
    <div className="border-b border-rule py-3">
      <dt className="font-display text-lg font-medium text-soft">{label}</dt>
      <dd className="text-lg">{children}</dd>
    </div>
  );
}

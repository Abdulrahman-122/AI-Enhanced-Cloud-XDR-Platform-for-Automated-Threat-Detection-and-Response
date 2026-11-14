import { Link, useParams } from "react-router-dom";
import { useApi } from "../api.js";
import Page from "../components/Page.jsx";
import { ErrorNote, Loading } from "../components/Status.jsx";
import { formatDate } from "../format.js";

export default function Post() {
  const { slug } = useParams();
  const post = useApi(`/api/posts/${encodeURIComponent(slug)}`);

  if (post.loading) return <Page><Loading what="article" /></Page>;
  if (post.error) {
    return (
      <Page title="Article not found">
        <ErrorNote error={post.error} retryHint="It may have moved." />
        <Link to="/news" className="link mt-6 inline-block font-display text-lg">Back to news</Link>
      </Page>
    );
  }

  const p = post.data;
  const paragraphs = (p.body || "").split(/\n\s*\n/).filter(Boolean);
  return (
    <Page title={p.title}>
      <Link to="/news" className="link font-display text-lg">← News and guides</Link>
      <article className="mx-auto mt-6 max-w-measure">
        <p className="font-display text-lg font-medium text-route">{p.category}</p>
        <h1 className="mt-2 text-[clamp(2.5rem,5vw,4rem)]">{p.title}</h1>
        <p className="mt-4 border-b border-rule pb-4 text-soft">
          {p.author} · {formatDate(p.published_at)}
        </p>
        <p className="mt-6 text-xl italic text-soft">{p.summary}</p>
        <div className="mt-8 space-y-5 text-[1.1rem]">
          {paragraphs.map((text, i) => (
            <p key={i}>{text}</p>
          ))}
        </div>
      </article>
    </Page>
  );
}

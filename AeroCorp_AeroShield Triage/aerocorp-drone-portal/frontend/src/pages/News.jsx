import { Link, useSearchParams } from "react-router-dom";
import { useApi } from "../api.js";
import Page from "../components/Page.jsx";
import Pager from "../components/Pager.jsx";
import { Empty, ErrorNote, Loading } from "../components/Status.jsx";
import { formatDate } from "../format.js";

export default function News() {
  const [params, setParams] = useSearchParams();
  const page = Number(params.get("page") || 1);
  const list = useApi(`/api/posts?page=${page}&limit=9`);

  return (
    <Page title="News and guides">
      <h1 className="text-[clamp(2.75rem,6vw,4.5rem)]">News and guides</h1>
      <p className="mt-3 max-w-measure text-lg text-soft">Regulation updates, product launches and operator guides from the AeroCorp editorial team.</p>

      <div className="mt-10">
        {list.loading && <Loading what="news" />}
        {list.error && <ErrorNote error={list.error} />}
        {list.data && list.data.items.length === 0 && <Empty title="No articles yet">Check back soon.</Empty>}
        {list.data && list.data.items.length > 0 && (
          <>
            <ul className="grid gap-6 md:grid-cols-3">
              {list.data.items.map((post) => (
                <li key={post.slug} className="flex flex-col border border-rule bg-paper p-6">
                  <p className="font-display text-base font-medium text-route">{post.category}</p>
                  <Link to={`/news/${encodeURIComponent(post.slug)}`} className="mt-2 text-[1.8rem] hover:text-route">
                    {post.title}
                  </Link>
                  <p className="mt-2 flex-1 text-soft">{post.summary}</p>
                  <p className="mt-4 border-t border-rule pt-3 text-[0.9rem] text-soft">
                    {post.author} · {formatDate(post.published_at)}
                  </p>
                </li>
              ))}
            </ul>
            <Pager page={list.data.page} pages={list.data.pages} onChange={(p) => setParams({ page: String(p) })} />
          </>
        )}
      </div>
    </Page>
  );
}

import { Link } from "react-router-dom";
import { useApi } from "../api.js";
import DroneCard from "../components/DroneCard.jsx";
import FlightRoute from "../components/FlightRoute.jsx";
import Page from "../components/Page.jsx";
import { ErrorNote, Loading } from "../components/Status.jsx";
import { formatDate } from "../format.js";

export default function Home() {
  const categories = useApi("/api/categories");
  const featured = useApi("/api/drones?sort=newest&limit=3");
  const news = useApi("/api/posts?limit=3");
  const total = (categories.data || []).reduce((sum, c) => sum + c.count, 0);

  return (
    <>
      <section className="border-b border-rule bg-paper">
        <Page className="md:py-20">
          <p className="font-display text-xl font-medium text-route">Aircraft for inspection, mapping, farming and delivery</p>
          <h1 className="mt-3 max-w-4xl text-[clamp(3rem,7vw,5.5rem)]">Fly the right aircraft for the job.</h1>
          <p className="mt-6 max-w-measure text-xl text-soft">
            AeroCorp supplies, supports and trains operators. Compare the catalogue, read the datasheets, and request a quote in one place.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to="/drones" className="btn">Browse aircraft</Link>
            <Link to="/contact" className="btn-quiet">Talk to our team</Link>
          </div>
        </Page>
      </section>

      <Page>
        <h2 className="text-4xl">Pick a route</h2>
        <p className="mt-2 max-w-measure text-soft">Each stop is an aircraft class. Start anywhere on the line.</p>
        <div className="mt-8">
          {categories.loading && <Loading what="catalogue" />}
          {categories.error && <ErrorNote error={categories.error} />}
          {categories.data && <FlightRoute categories={categories.data} total={total} />}
        </div>
      </Page>

      <section className="border-t border-rule bg-paper">
        <Page>
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <h2 className="text-4xl">Featured aircraft</h2>
            <Link to="/drones" className="link font-display text-lg">See all aircraft</Link>
          </div>
          <div className="mt-6">
            {featured.loading && <Loading what="aircraft" />}
            {featured.error && <ErrorNote error={featured.error} />}
            {featured.data && (
              <div className="grid gap-6 md:grid-cols-3">
                {featured.data.items.map((drone) => (
                  <DroneCard key={drone.slug} drone={drone} showCategory />
                ))}
              </div>
            )}
          </div>
        </Page>
      </section>

      <Page>
        <div className="flex flex-wrap items-baseline justify-between gap-3">
          <h2 className="text-4xl">From the news desk</h2>
          <Link to="/news" className="link font-display text-lg">All news</Link>
        </div>
        <div className="mt-6">
          {news.loading && <Loading what="news" />}
          {news.error && <ErrorNote error={news.error} />}
          {news.data && (
            <ul className="divide-y divide-rule border-y border-rule">
              {news.data.items.map((post) => (
                <li key={post.slug} className="py-5">
                  <p className="font-display text-base font-medium text-route">
                    {post.category} · {formatDate(post.published_at)}
                  </p>
                  <Link to={`/news/${encodeURIComponent(post.slug)}`} className="mt-1 block text-[1.9rem] hover:text-route">
                    {post.title}
                  </Link>
                  <p className="mt-1 max-w-measure text-soft">{post.summary}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Page>
    </>
  );
}

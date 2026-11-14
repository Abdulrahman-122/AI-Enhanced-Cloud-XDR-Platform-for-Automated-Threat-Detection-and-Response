import { useSearchParams } from "react-router-dom";
import { useApi } from "../api.js";
import DroneCard from "../components/DroneCard.jsx";
import Page from "../components/Page.jsx";
import Pager from "../components/Pager.jsx";
import { Empty, ErrorNote, Loading } from "../components/Status.jsx";

const SORTS = [
  ["name", "Name, A to Z"],
  ["price", "Price, low to high"],
  ["newest", "Newest first"],
];

export default function Drones() {
  const [params, setParams] = useSearchParams();
  const category = params.get("category") || "";
  const sort = params.get("sort") || "name";
  const page = Number(params.get("page") || 1);

  const categories = useApi("/api/categories");
  const query = new URLSearchParams({ sort, page: String(page), limit: "12" });
  if (category) query.set("category", category);
  const list = useApi(`/api/drones?${query}`);

  function update(changes) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value);
      else next.delete(key);
    }
    if (!("page" in changes)) next.delete("page"); // a new filter starts again from page 1
    setParams(next);
  }

  const total = (categories.data || []).reduce((sum, c) => sum + c.count, 0);

  return (
    <Page title="Aircraft">
      <h1 className="text-[clamp(2.75rem,6vw,4.5rem)]">Aircraft</h1>
      <p className="mt-3 max-w-measure text-lg text-soft">{total} aircraft in the catalogue. Filter by class, then sort.</p>

      <div className="mt-8 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by class">
        <FilterChip active={!category} onClick={() => update({ category: "" })}>
          All ({total})
        </FilterChip>
        {(categories.data || []).map((c) => (
          <FilterChip key={c.name} active={category === c.name} onClick={() => update({ category: c.name })}>
            {c.name} ({c.count})
          </FilterChip>
        ))}
      </div>

      <div className="mt-6 flex items-center gap-3">
        <label htmlFor="sort" className="font-display text-lg font-medium">Sort by</label>
        <select id="sort" className="field w-auto" value={sort} onChange={(e) => update({ sort: e.target.value })}>
          {SORTS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-8">
        {list.loading && <Loading what="aircraft" />}
        {list.error && <ErrorNote error={list.error} />}
        {list.data && list.data.items.length === 0 && (
          <Empty title="No aircraft found">Try another class.</Empty>
        )}
        {list.data && list.data.items.length > 0 && (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {list.data.items.map((drone) => (
                <DroneCard key={drone.slug} drone={drone} showCategory={!category} />
              ))}
            </div>
            <Pager page={list.data.page} pages={list.data.pages} onChange={(p) => update({ page: String(p) })} />
          </>
        )}
      </div>
    </Page>
  );
}

function FilterChip({ active, onClick, children }) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onClick}
      className={`border px-3 py-1.5 font-display text-lg font-medium transition-colors ${
        active ? "border-route bg-route text-white" : "border-rule bg-paper text-ink hover:border-ink"
      }`}
    >
      {children}
    </button>
  );
}

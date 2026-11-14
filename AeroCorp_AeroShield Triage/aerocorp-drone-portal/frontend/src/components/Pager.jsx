/** Previous / next controls for paged API results. Renders nothing when there is only one page. */
export default function Pager({ page, pages, onChange }) {
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pages" className="mt-10 flex items-center justify-center gap-4 font-display text-lg">
      <button className="btn-quiet px-4 py-1.5 disabled:opacity-40" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        Previous
      </button>
      <span className="tabular">
        Page {page} of {pages}
      </span>
      <button className="btn-quiet px-4 py-1.5 disabled:opacity-40" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next
      </button>
    </nav>
  );
}

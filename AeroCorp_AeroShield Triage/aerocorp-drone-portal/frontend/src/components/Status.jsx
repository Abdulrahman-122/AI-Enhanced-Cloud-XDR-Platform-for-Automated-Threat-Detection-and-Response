export function Loading({ what = "page" }) {
  return (
    <p role="status" className="py-12 font-display text-xl text-soft">
      Loading the {what}…
    </p>
  );
}

export function ErrorNote({ error, retryHint = "Try again in a moment." }) {
  return (
    <div role="alert" className="border border-route bg-paper p-5">
      <p className="font-display text-xl font-semibold text-route">Something went wrong</p>
      <p className="mt-1 text-soft">{error?.detail || error?.message || "The request failed."} {retryHint}</p>
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="border border-dashed border-rule p-8">
      <p className="font-display text-2xl font-semibold">{title}</p>
      <div className="mt-1 text-soft">{children}</div>
    </div>
  );
}

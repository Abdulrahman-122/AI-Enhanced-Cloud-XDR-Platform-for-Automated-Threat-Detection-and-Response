import { useEffect } from "react";

/** Standard page width and top padding, and sets the browser tab title. */
export default function Page({ title, children, className = "" }) {
  useEffect(() => {
    document.title = title ? `${title} | AeroCorp` : "AeroCorp Drone Portal";
  }, [title]);
  return <div className={`mx-auto w-full max-w-6xl px-4 py-10 md:px-6 md:py-14 ${className}`}>{children}</div>;
}

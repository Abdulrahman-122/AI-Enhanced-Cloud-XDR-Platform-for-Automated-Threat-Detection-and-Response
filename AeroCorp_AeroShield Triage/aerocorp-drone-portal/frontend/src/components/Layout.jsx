import { useState } from "react";
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useApi } from "../api.js";
import { useAuth } from "../auth.jsx";
import Newsletter from "./Newsletter.jsx";

function Mark() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
      <rect width="32" height="32" fill="#0F2540" />
      <path d="M5 24 Q12 6 27 9" fill="none" stroke="#FF6FA8" strokeWidth="3" strokeLinecap="round" />
      <circle cx="27" cy="9" r="3" fill="#FF6FA8" />
    </svg>
  );
}

const navClass = ({ isActive }) =>
  `font-display text-xl font-medium hover:text-route ${isActive ? "text-route underline decoration-2 underline-offset-[10px]" : ""}`;

export default function Layout() {
  const navigate = useNavigate();
  const { session, logout } = useAuth();
  const isStaff = session?.role === "admin" || session?.role === "sales";
  const health = useApi("/api/health");
  const [term, setTerm] = useState("");
  const labBuild = health.data?.mode === "vulnerable";

  function submit(event) {
    event.preventDefault();
    const q = term.trim();
    if (q) navigate(`/search?q=${encodeURIComponent(q)}`);
  }

  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:bg-ink focus:px-3 focus:py-2 focus:text-chart">
        Skip to content
      </a>

      {labBuild && (
        <div role="note" className="bg-ink text-chart">
          <p className="mx-auto max-w-6xl px-4 py-2 text-[0.95rem] md:px-6">
            Training build with deliberate security flaws. Run it only on an isolated lab network.
          </p>
        </div>
      )}

      <header className="border-b border-rule bg-paper">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-8 gap-y-3 px-4 py-4 md:px-6">
          <Link to="/" className="flex items-center gap-2.5" aria-label="AeroCorp home">
            <Mark />
            <span className="font-display text-[1.9rem] font-bold leading-none tracking-tight">AeroCorp</span>
          </Link>
          <nav aria-label="Main" className="flex gap-6">
            <NavLink to="/drones" className={navClass}>Aircraft</NavLink>
            <NavLink to="/news" className={navClass}>News</NavLink>
            <NavLink to="/contact" className={navClass}>Contact</NavLink>
            <NavLink to={session?.role === "customer" ? "/account" : "/account/login"} className={navClass}>{session?.role === "customer" ? "My account" : "Sign in"}</NavLink>
          </nav>
          <form onSubmit={submit} role="search" className="ml-auto flex w-full gap-2 sm:w-auto">
            <label htmlFor="site-search" className="sr-only">Search aircraft and news</label>
            <input
              id="site-search"
              name="q"
              type="search"
              placeholder="Search aircraft"
              value={term}
              onChange={(event) => setTerm(event.target.value)}
              className="field w-full sm:w-64"
            />
            <button className="btn-quiet px-4">Search</button>
          </form>
        </div>
      </header>

      <main id="main" className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-rule bg-paper">
        <div className="mx-auto grid max-w-6xl gap-10 px-4 py-12 md:grid-cols-[1.5fr_1fr_1fr] md:px-6">
          <Newsletter />
          <nav aria-label="Footer">
            <h2 className="text-2xl">Browse</h2>
            <ul className="mt-2 space-y-1">
              <li><Link className="link" to="/drones">All aircraft</Link></li>
              <li><Link className="link" to="/news">News and guides</Link></li>
              <li><Link className="link" to="/contact">Contact us</Link></li>
            </ul>
          </nav>
          <div>
            <h2 className="text-2xl">Staff</h2>
            <ul className="mt-2 space-y-1">
              {isStaff ? (
                <>
                  <li><Link className="link" to="/admin">Inbox, aircraft and newsletters</Link></li>
                  <li><button className="link" onClick={() => { logout(); navigate("/"); }}>Sign out</button></li>
                </>
              ) : (
                <li><Link className="link" to="/login">Staff sign-in</Link></li>
              )}
            </ul>
          </div>
        </div>
      </footer>
    </div>
  );
}

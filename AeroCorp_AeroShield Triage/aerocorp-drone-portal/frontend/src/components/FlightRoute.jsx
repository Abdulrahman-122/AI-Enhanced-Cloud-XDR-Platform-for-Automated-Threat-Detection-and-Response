import { Link, useNavigate } from "react-router-dom";

const W = 1200;
const H = 320;
const MARGIN = 110;
const DRAW_SECONDS = 2.8;
const START_DELAY = 0.25;

/** Smooth curve through the stops (Catmull-Rom converted to cubic Béziers). */
function smoothPath(points) {
  let d = `M${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i - 1] || points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] || p2;
    const c1 = { x: p1.x + (p2.x - p0.x) / 6, y: p1.y + (p2.y - p0.y) / 6 };
    const c2 = { x: p2.x - (p3.x - p1.x) / 6, y: p2.y - (p3.y - p1.y) / 6 };
    d += ` C${c1.x.toFixed(1)} ${c1.y.toFixed(1)} ${c2.x.toFixed(1)} ${c2.y.toFixed(1)} ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`;
  }
  return d;
}

/**
 * The catalogue classes as stops on one flight route, ending at "All aircraft".
 * Large screens get the drawn route; small screens get the same stops as a plain list.
 */
export default function FlightRoute({ categories, total }) {
  const navigate = useNavigate();
  const stops = [
    ...categories.map((c) => ({ label: c.name, sub: `${c.count} aircraft`, to: `/drones?category=${encodeURIComponent(c.name)}` })),
    { label: "All aircraft", sub: `${total} in the catalogue`, to: "/drones", final: true },
  ];
  const n = stops.length;
  const points = stops.map((_, i) => ({
    x: MARGIN + (i * (W - 2 * MARGIN)) / (n - 1),
    y: H / 2 + 58 * Math.sin(i * 1.15 + 0.5) * (i === n - 1 ? 0.4 : 1),
  }));
  const lengths = points.slice(1).map((p, i) => Math.hypot(p.x - points[i].x, p.y - points[i].y));
  const totalLength = lengths.reduce((a, b) => a + b, 0);
  let travelled = 0;
  const reachedAt = [0, ...lengths.map((len) => (travelled += len) / totalLength)];
  const path = smoothPath(points);

  const go = (to) => () => navigate(to);
  const onKey = (to) => (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      navigate(to);
    }
  };

  return (
    <figure>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="hidden w-full border border-rule bg-paper md:block"
        role="group"
        aria-label="Catalogue classes shown as stops on a flight route"
      >
        {Array.from({ length: 13 }, (_, i) => (
          <line key={`v${i}`} x1={i * 100} y1="0" x2={i * 100} y2={H} stroke="#AEBFCE" strokeWidth="1" opacity="0.55" />
        ))}
        {Array.from({ length: 7 }, (_, i) => (
          <line key={`h${i}`} x1="0" y1={i * 55} x2={W} y2={i * 55} stroke="#AEBFCE" strokeWidth="1" opacity="0.55" />
        ))}
        <path d={path} fill="none" stroke="#46607C" strokeWidth="2" strokeDasharray="3 8" strokeLinecap="round" opacity="0.7" />
        <path d={path} pathLength="1" className="route-line" fill="none" stroke="#B0125A" strokeWidth="4" strokeLinecap="round" />

        {stops.map((stop, i) => {
          const { x, y } = points[i];
          const above = i % 2 === 0;
          const delay = START_DELAY + reachedAt[i] * DRAW_SECONDS;
          const textY = above ? y - 40 : y + 46;
          return (
            <g
              key={stop.label}
              className="route-stop"
              style={{ animationDelay: `${delay.toFixed(2)}s` }}
              role="link"
              tabIndex={0}
              aria-label={`${stop.label}, ${stop.sub}`}
              onClick={go(stop.to)}
              onKeyDown={onKey(stop.to)}
            >
              <circle cx={x} cy={y} r="30" fill="transparent" />
              <circle className="stop-dot" cx={x} cy={y} r={stop.final ? 11 : 8} fill={stop.final ? "#B0125A" : "#F5F8FA"} stroke="#B0125A" strokeWidth="3.5" />
              <text className="stop-name" x={x} y={textY} textAnchor="middle" fill="#0F2540" fontFamily="'Barlow Condensed', sans-serif" fontWeight="600" fontSize="23">
                {stop.label}
              </text>
              <text x={x} y={textY + 20} textAnchor="middle" fill="#46607C" fontFamily="'Barlow Condensed', sans-serif" fontWeight="500" fontSize="17">
                {stop.sub}
              </text>
            </g>
          );
        })}
      </svg>

      <ul className="border-l-2 border-route pl-5 md:hidden">
        {stops.map((stop) => (
          <li key={stop.label} className="relative py-2">
            <span className="absolute -left-[1.62rem] top-[1.05rem] h-3 w-3 rounded-full border-2 border-route bg-paper" aria-hidden="true" />
            <Link to={stop.to} className="font-display text-2xl font-semibold hover:text-route">
              {stop.label}
            </Link>
            <span className="block text-[0.95rem] text-soft">{stop.sub}</span>
          </li>
        ))}
      </ul>
      <figcaption className="mt-3 text-[0.95rem] text-soft">Pick a stop to see the aircraft in that class.</figcaption>
    </figure>
  );
}

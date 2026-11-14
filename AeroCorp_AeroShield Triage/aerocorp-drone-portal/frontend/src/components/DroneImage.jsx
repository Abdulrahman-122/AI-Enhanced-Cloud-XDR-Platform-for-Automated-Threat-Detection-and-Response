import { useState } from "react";
import { FIXED_WING } from "../format.js";

/** Chart-style drawing used until a real photo exists (or when a photo fails to load). */
function Illustration({ category, name }) {
  const wing = FIXED_WING.has(category);
  return (
    <svg viewBox="0 0 400 300" className="h-full w-full bg-chart" role="img" aria-label={`Drawing of ${name}`} preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern id="chart-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M40 0H0V40" fill="none" stroke="#AEBFCE" strokeWidth="1" opacity="0.7" />
        </pattern>
      </defs>
      <rect width="400" height="300" fill="url(#chart-grid)" />
      {wing ? (
        <g fill="#0F2540" stroke="#0F2540" strokeLinejoin="round">
          <path d="M200 58c12 0 16 22 16 60l0 78c0 14-6 26-16 26s-16-12-16-26l0-78c0-38 4-60 16-60z" />
          <path d="M184 120L52 156l0 16 132-22zM216 120l132 36 0 16-132-22z" fill="#F5F8FA" strokeWidth="3" />
          <path d="M186 212l-38 18 0 10 38-10zM214 212l38 18 0 10-38-10z" fill="#F5F8FA" strokeWidth="3" />
          <circle cx="200" cy="74" r="6" fill="#B0125A" stroke="none" />
        </g>
      ) : (
        <g stroke="#0F2540" strokeWidth="5" strokeLinecap="round">
          <path d="M200 150L132 88M200 150L268 88M200 150L132 212M200 150L268 212" />
          {[[132, 88], [268, 88], [132, 212], [268, 212]].map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="36" fill="#F5F8FA" strokeWidth="3" strokeDasharray="6 5" />
          ))}
          <rect x="174" y="126" width="52" height="48" rx="8" fill="#0F2540" />
          <circle cx="200" cy="180" r="7" fill="#B0125A" stroke="none" />
        </g>
      )}
    </svg>
  );
}

export default function DroneImage({ drone, eager = false }) {
  const [failed, setFailed] = useState(false);
  if (drone.image_url && !failed) {
    return (
      <img
        src={drone.image_url}
        alt={drone.name}
        loading={eager ? "eager" : "lazy"}
        onError={() => setFailed(true)}
        className="h-full w-full object-cover"
      />
    );
  }
  return <Illustration category={drone.category} name={drone.name} />;
}

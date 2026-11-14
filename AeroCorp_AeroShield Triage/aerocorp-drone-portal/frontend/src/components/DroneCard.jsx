import { Link } from "react-router-dom";
import DroneImage from "./DroneImage.jsx";
import { formatPrice, headlineStat } from "../format.js";

export default function DroneCard({ drone, showCategory = false }) {
  const stat = headlineStat(drone.specs);
  return (
    <Link
      to={`/drones/${encodeURIComponent(drone.slug)}`}
      className="group flex h-full flex-col border border-rule bg-paper transition-colors hover:border-route"
    >
      <div className="aspect-[4/3] overflow-hidden border-b border-rule">
        <DroneImage drone={drone} />
      </div>
      <div className="flex flex-1 flex-col p-4">
        {showCategory && <p className="font-display text-base font-medium text-route">{drone.category}</p>}
        <h3 className="text-[1.65rem] group-hover:underline group-hover:decoration-route group-hover:underline-offset-4">{drone.name}</h3>
        <p className="text-[0.95rem] text-soft">{drone.manufacturer}</p>
        <div className="tabular mt-auto flex items-baseline justify-between gap-3 border-t border-rule pt-3 font-display text-lg">
          <span>{stat}</span>
          <span className="text-soft">{formatPrice(drone.price_usd)}</span>
        </div>
      </div>
    </Link>
  );
}

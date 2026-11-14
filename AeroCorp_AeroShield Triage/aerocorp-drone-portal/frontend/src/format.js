export const SPEC_META = {
  flight_time_min: ["Flight time", "min"],
  endurance_h: ["Endurance", "h"],
  max_range_km: ["Max range", "km"],
  max_speed_kmh: ["Max speed", "km/h"],
  ceiling_m: ["Service ceiling", "m"],
  weight_kg: ["Weight", "kg"],
  payload_kg: ["Payload", "kg"],
  wingspan_m: ["Wingspan", "m"],
  camera: ["Camera", ""],
  ip_rating: ["Ingress protection", ""],
  notes: ["Notes", ""],
};

export function specRows(specs = {}) {
  return Object.entries(SPEC_META)
    .filter(([key]) => specs[key] !== undefined && specs[key] !== null && specs[key] !== "")
    .map(([key, [label, unit]]) => {
      const value = specs[key];
      const text = typeof value === "number" ? value.toLocaleString("en-US") : String(value);
      return { key, label, value: unit ? `${text} ${unit}` : text };
    });
}

/** The single most useful figure for a catalogue plate. */
export function headlineStat(specs = {}) {
  if (specs.flight_time_min) return `${specs.flight_time_min} min flight`;
  if (specs.endurance_h) return `${specs.endurance_h} h endurance`;
  if (specs.payload_kg) return `${specs.payload_kg.toLocaleString("en-US")} kg payload`;
  if (specs.max_range_km) return `${specs.max_range_km} km range`;
  return "";
}

export const formatPrice = (usd) => (usd ? `From US$${usd.toLocaleString("en-US")}` : "Price on request");

export function formatDate(iso) {
  try {
    return new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", year: "numeric" }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export const FIXED_WING = new Set(["Mapping & survey", "Long-endurance", "Delivery & logistics"]);

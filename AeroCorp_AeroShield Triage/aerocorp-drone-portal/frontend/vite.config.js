import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the Vite server forwards API calls (and the files scanners look for) to FastAPI.
const target = process.env.VITE_API_TARGET || "http://127.0.0.1:8000";
const proxied = Object.fromEntries(
  ["/api", "/robots.txt", "/.env", "/backup"].map((path) => [path, { target, changeOrigin: false }])
);

export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", port: 5173, proxy: proxied },
  preview: { host: "127.0.0.1", port: 4173, proxy: proxied },
});

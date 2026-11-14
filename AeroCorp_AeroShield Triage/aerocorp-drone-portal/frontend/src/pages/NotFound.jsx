import { Link } from "react-router-dom";
import Page from "../components/Page.jsx";

export default function NotFound() {
  return (
    <Page title="Page not found">
      <p className="font-display text-xl font-medium text-route">Error 404</p>
      <h1 className="mt-2 text-[clamp(2.75rem,6vw,4.5rem)]">Off the flight path.</h1>
      <p className="mt-4 max-w-measure text-lg text-soft">The page you asked for does not exist or has moved.</p>
      <div className="mt-8 flex gap-3">
        <Link to="/" className="btn">Go to the home page</Link>
        <Link to="/drones" className="btn-quiet">Browse aircraft</Link>
      </div>
    </Page>
  );
}

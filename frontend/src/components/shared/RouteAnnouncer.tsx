import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";

/**
 * Announces page navigation to screen readers in an SPA.
 * Uses aria-live="assertive" so route changes are announced immediately.
 */
export function RouteAnnouncer() {
  const location = useLocation();
  const [announcement, setAnnouncement] = useState("");

  useEffect(() => {
    // Build a meaningful announcement from the document title or pathname
    const title = document.title;
    if (title) {
      setAnnouncement(`Navigated to ${title}`);
    } else {
      const page = location.pathname.replace(/\//g, " ").trim() || "home";
      setAnnouncement(`Navigated to ${page}`);
    }
  }, [location.pathname]);

  return (
    <div
      role="status"
      aria-live="assertive"
      aria-atomic="true"
      className="sr-only"
    >
      {announcement}
    </div>
  );
}

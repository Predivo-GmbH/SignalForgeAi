import { useEffect } from "react";

/**
 * Adds a `<meta name="robots" content="noindex">` tag while the component
 * is mounted, then removes it on unmount.
 */
export function useNoIndex() {
  useEffect(() => {
    const meta = document.createElement("meta");
    meta.name = "robots";
    meta.content = "noindex";
    document.head.appendChild(meta);
    return () => {
      document.head.removeChild(meta);
    };
  }, []);
}

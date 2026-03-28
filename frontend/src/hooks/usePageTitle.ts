import { useEffect } from "react";

const SUFFIX = "SignalForgeAI";

/**
 * Sets `document.title` for the current page.
 * Pass `null` to use just the app name (landing / home).
 */
export function usePageTitle(title: string | null) {
  useEffect(() => {
    document.title = title ? `${title} | ${SUFFIX}` : SUFFIX;
  }, [title]);
}

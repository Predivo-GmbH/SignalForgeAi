/**
 * Read a CSS custom property value from :root at runtime.
 * Falls back to the provided default if the property is not set.
 */
export function cssVar(name: string, fallback = ""): string {
  if (typeof document === "undefined") return fallback;
  return (
    getComputedStyle(document.documentElement)
      .getPropertyValue(name)
      .trim() || fallback
  );
}

/** Convenience: read multiple vars at once into an object. */
export function cssVars<K extends string>(
  map: Record<K, string>,
): Record<K, string> {
  const result = {} as Record<K, string>;
  for (const key in map) {
    result[key] = cssVar(map[key]);
  }
  return result;
}

import { useState } from "react";
import { cssVar } from "@/lib/colors";

const DONUT_COLOR_VARS = [
  "--color-palette-blue",
  "--color-palette-amber",
  "--color-palette-emerald",
  "--color-palette-violet",
  "--color-palette-rose",
  "--color-palette-cyan",
  "--color-palette-orange",
  "--color-palette-pink",
  "--color-palette-teal",
  "--color-palette-indigo",
] as const;

export function getDonutColors(): string[] {
  return DONUT_COLOR_VARS.map((v) => cssVar(v));
}

export { DONUT_COLOR_VARS };

export function CoinIcon({ symbol, imageUrl, size = 24 }: { symbol: string; imageUrl: string | null; size?: number }) {
  const [error, setError] = useState(false);

  if (imageUrl && !error) {
    return (
      <img
        src={imageUrl}
        alt={symbol}
        width={size}
        height={size}
        className="rounded-full shrink-0"
        onError={() => setError(true)}
        loading="lazy"
      />
    );
  }

  const colorIndex = symbol.charCodeAt(0) % DONUT_COLOR_VARS.length;
  return (
    <div
      className="rounded-full shrink-0 flex items-center justify-center text-white font-bold"
      style={{ width: size, height: size, backgroundColor: cssVar(DONUT_COLOR_VARS[colorIndex]), fontSize: size * 0.45 }}
    >
      {symbol.charAt(0)}
    </div>
  );
}

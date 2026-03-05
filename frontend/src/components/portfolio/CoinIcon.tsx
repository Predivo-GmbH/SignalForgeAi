import { useState } from "react";

const DONUT_COLORS = [
  "#3b82f6", // blue
  "#f59e0b", // amber
  "#10b981", // emerald
  "#8b5cf6", // violet
  "#f43f5e", // rose
  "#06b6d4", // cyan
  "#f97316", // orange
  "#ec4899", // pink
  "#14b8a6", // teal
  "#6366f1", // indigo
];

export { DONUT_COLORS };

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

  const colorIndex = symbol.charCodeAt(0) % DONUT_COLORS.length;
  return (
    <div
      className="rounded-full shrink-0 flex items-center justify-center text-white font-bold"
      style={{ width: size, height: size, backgroundColor: DONUT_COLORS[colorIndex], fontSize: size * 0.45 }}
    >
      {symbol.charAt(0)}
    </div>
  );
}

import { useState } from "react";
import { fmtUsd } from "@/lib/format";

/* ---- Helpers ---- */

function fmtCompact(val: number): string {
  if (val >= 1e12) return `$${(val / 1e12).toFixed(2)}T`;
  if (val >= 1e9) return `$${(val / 1e9).toFixed(2)}B`;
  if (val >= 1e6) return `$${(val / 1e6).toFixed(1)}M`;
  if (val >= 1e3) return `$${(val / 1e3).toFixed(1)}K`;
  return fmtUsd(val);
}

/* ---- Types ---- */

export interface DonutSlice {
  label: string;
  value: number;
  pct: number;
  color: string;
}

/* ---- Component ---- */

export function DonutChart({
  slices,
  totalValue,
  onSliceClick,
}: {
  slices: DonutSlice[];
  totalValue: number;
  onSliceClick?: (label: string) => void;
}) {
  const size = 180;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 80;
  const innerR = 56;
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  // Build arcs
  let cumAngle = -90; // start at top
  const arcs = slices.map((s, i) => {
    const angle = (s.pct / 100) * 360;
    const startAngle = cumAngle;
    cumAngle += angle;
    const endAngle = cumAngle;
    const largeArc = angle > 180 ? 1 : 0;

    const r = outerR;
    const ir = innerR;

    const toRad = (a: number) => (a * Math.PI) / 180;
    const x1o = cx + r * Math.cos(toRad(startAngle));
    const y1o = cy + r * Math.sin(toRad(startAngle));
    const x2o = cx + r * Math.cos(toRad(endAngle));
    const y2o = cy + r * Math.sin(toRad(endAngle));
    const x1i = cx + ir * Math.cos(toRad(endAngle));
    const y1i = cy + ir * Math.sin(toRad(endAngle));
    const x2i = cx + ir * Math.cos(toRad(startAngle));
    const y2i = cy + ir * Math.sin(toRad(startAngle));

    const d = [
      `M ${x1o} ${y1o}`,
      `A ${r} ${r} 0 ${largeArc} 1 ${x2o} ${y2o}`,
      `L ${x1i} ${y1i}`,
      `A ${ir} ${ir} 0 ${largeArc} 0 ${x2i} ${y2i}`,
      "Z",
    ].join(" ");

    return { d, color: s.color, label: s.label, pct: s.pct, value: s.value, idx: i };
  });

  const hovered = hoveredIdx != null ? slices[hoveredIdx] : null;

  return (
    <div className="flex justify-center">
      <svg
        viewBox={`0 0 ${size} ${size}`}
        className="w-full h-auto max-w-[240px]"
      >
        {arcs.map((arc) => (
          <path
            key={arc.idx}
            d={arc.d}
            fill={arc.color}
            opacity={hoveredIdx != null && hoveredIdx !== arc.idx ? 0.35 : 1}
            className="transition-opacity duration-150"
            onMouseEnter={() => setHoveredIdx(arc.idx)}
            onMouseLeave={() => setHoveredIdx(null)}
            onClick={() => onSliceClick?.(arc.label)}
            style={{ cursor: "pointer" }}
          />
        ))}
        {/* Center text — switches between total and hovered slice */}
        {hovered ? (
          <>
            <text x={cx} y={cy - 14} textAnchor="middle" className="fill-(--color-text-secondary)" fontSize="8">
              {hovered.label}
            </text>
            <text x={cx} y={cy + 2} textAnchor="middle" className="fill-(--color-text-primary) font-bold" fontSize="12">
              {fmtUsd(hovered.value)}
            </text>
            <text x={cx} y={cy + 16} textAnchor="middle" className="fill-(--color-text-secondary) font-medium" fontSize="9">
              {hovered.pct.toFixed(1)}%
            </text>
          </>
        ) : (
          <>
            <text x={cx} y={cy - 8} textAnchor="middle" className="fill-(--color-text-secondary)" fontSize="8">
              Total Value
            </text>
            <text x={cx} y={cy + 10} textAnchor="middle" className="fill-(--color-text-primary) font-bold" fontSize="13">
              {fmtCompact(totalValue)}
            </text>
          </>
        )}
      </svg>
    </div>
  );
}

import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type ISeriesApi,
  type Time,
  ColorType,
} from "lightweight-charts";
import { cssVar } from "@/lib/colors";
import type { EquityPoint } from "@/hooks/useAnalytics";

interface EquityCurveProps {
  points: EquityPoint[];
}

export function EquityCurve({ points }: EquityCurveProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Create chart once on mount
  useEffect(() => {
    if (!containerRef.current) return;

    const bgSurface = cssVar("--color-bg-surface");
    const textSec = cssVar("--color-text-secondary");
    const border = cssVar("--color-border");
    const accent = cssVar("--color-accent");

    const chart = createChart(containerRef.current, {
      layout: {
        background: {
          type: ColorType.Solid,
          color: bgSurface,
        },
        textColor: textSec,
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: border },
        horzLines: { color: border },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      crosshair: {
        vertLine: {
          color: accent,
          width: 1,
          labelBackgroundColor: accent,
        },
        horzLine: {
          color: accent,
          width: 1,
          labelBackgroundColor: accent,
        },
      },
      timeScale: {
        borderColor: border,
      },
      rightPriceScale: {
        borderColor: border,
      },
    });

    const series = chart.addSeries(LineSeries, {
      color: accent,
      lineWidth: 2,
      crosshairMarkerBackgroundColor: accent,
      lastValueVisible: true,
      priceLineVisible: false,
    });

    chartRef.current = chart;
    seriesRef.current = series;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    observer.observe(containerRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
    };
  }, []);

  // Update data when points change
  useEffect(() => {
    if (!seriesRef.current || !points.length) return;

    // Deduplicate by date (keep last point per day) since lightweight-charts
    // requires unique, ascending time values and the API returns full datetimes.
    const byDate = new Map<string, number>();
    for (const p of points) {
      byDate.set(p.date.slice(0, 10), p.equity);
    }
    const data = Array.from(byDate, ([time, value]) => ({
      time: time as Time,
      value,
    }));

    seriesRef.current.setData(data);
    chartRef.current?.timeScale().fitContent();
  }, [points]);

  if (points.length === 0) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-4 sm:p-6 flex items-center justify-center h-[250px] sm:h-[350px]">
        <p className="text-sm text-(--color-text-secondary)">
          No equity data available
        </p>
      </div>
    );
  }

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-(--color-border)">
        <h3 className="text-sm font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Equity Curve
        </h3>
      </div>
      <div ref={containerRef} className="h-[250px] sm:h-[350px]" />
    </div>
  );
}

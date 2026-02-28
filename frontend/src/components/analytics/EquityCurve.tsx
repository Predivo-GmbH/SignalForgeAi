import { useEffect, useRef } from "react";
import {
  createChart,
  LineSeries,
  type IChartApi,
  type Time,
  ColorType,
} from "lightweight-charts";
import type { EquityPoint } from "@/hooks/useAnalytics";

interface EquityCurveProps {
  points: EquityPoint[];
}

export function EquityCurve({ points }: EquityCurveProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current || points.length === 0) return;

    const isDark = document.documentElement.classList.contains("dark");

    const chart = createChart(containerRef.current, {
      layout: {
        background: {
          type: ColorType.Solid,
          color: isDark ? "#141420" : "#FFFFFF",
        },
        textColor: isDark ? "#8B8BA0" : "#6B6B80",
      },
      grid: {
        vertLines: { color: isDark ? "#2A2A3C" : "#E5E2DC" },
        horzLines: { color: isDark ? "#2A2A3C" : "#E5E2DC" },
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      crosshair: {
        vertLine: {
          color: "#7B61FF",
          width: 1,
          labelBackgroundColor: "#7B61FF",
        },
        horzLine: {
          color: "#7B61FF",
          width: 1,
          labelBackgroundColor: "#7B61FF",
        },
      },
      timeScale: {
        borderColor: isDark ? "#2A2A3C" : "#E5E2DC",
      },
      rightPriceScale: {
        borderColor: isDark ? "#2A2A3C" : "#E5E2DC",
      },
    });

    chartRef.current = chart;

    const series = chart.addSeries(LineSeries, {
      color: "#7B61FF",
      lineWidth: 2,
      crosshairMarkerBackgroundColor: "#7B61FF",
      lastValueVisible: true,
      priceLineVisible: false,
    });

    const data = points.map((p) => ({
      time: p.date as Time,
      value: p.equity,
    }));

    series.setData(data);
    chart.timeScale().fitContent();

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
    };
  }, [points]);

  if (points.length === 0) {
    return (
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 flex items-center justify-center h-[350px]">
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
      <div ref={containerRef} className="h-[350px]" />
    </div>
  );
}

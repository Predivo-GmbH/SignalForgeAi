import { useState, useRef, useCallback, useEffect } from "react";
import { Info } from "lucide-react";

interface TooltipProps {
  text?: string;
  /** Rich content — takes priority over text when provided. */
  content?: React.ReactNode;
  /** Widens the tooltip to w-80 (320px) for rich content. */
  wide?: boolean;
  /** When true, renders the default Info icon trigger (same as omitting children). */
  icon?: boolean;
  children?: React.ReactNode;
}

export function Tooltip({ text, content, wide, children }: TooltipProps) {
  const [show, setShow] = useState(false);
  const [coords, setCoords] = useState({ left: 0, top: 0, pos: "bottom" as "top" | "bottom" });
  const ref = useRef<HTMLSpanElement>(null);
  const tooltipWidth = wide ? 320 : 256; // w-80 or w-64
  const gap = 8;

  const computePosition = useCallback(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    const vw = window.innerWidth;
    const centerX = rect.left + rect.width / 2;

    // Clamp horizontally so tooltip stays within viewport (8px margin)
    const halfW = tooltipWidth / 2;
    const margin = 8;
    const left = Math.max(margin + halfW, Math.min(centerX, vw - margin - halfW));

    // Show below if near top of viewport, otherwise above
    if (rect.top < 100) {
      setCoords({ left, top: rect.bottom + gap, pos: "bottom" });
    } else {
      setCoords({ left, top: rect.top - gap, pos: "top" });
    }
  }, [tooltipWidth]);

  const handleEnter = useCallback(() => {
    computePosition();
    setShow(true);
  }, [computePosition]);

  // Tap-to-toggle for touch devices
  const handleClick = useCallback(
    (e: React.MouseEvent | React.TouchEvent) => {
      // Only handle as tap-toggle on touch devices (no hover)
      // Check if this was likely a touch event
      if ("touches" in e || (window.matchMedia("(pointer: coarse)").matches)) {
        e.preventDefault();
        if (show) {
          setShow(false);
        } else {
          computePosition();
          setShow(true);
        }
      }
    },
    [show, computePosition],
  );

  // Dismiss tooltip when tapping elsewhere on mobile
  useEffect(() => {
    if (!show) return;
    const dismiss = (e: TouchEvent | MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setShow(false);
      }
    };
    // Small delay so the current tap doesn't immediately dismiss
    const id = setTimeout(() => {
      document.addEventListener("touchstart", dismiss, { passive: true });
      document.addEventListener("mousedown", dismiss);
    }, 10);
    return () => {
      clearTimeout(id);
      document.removeEventListener("touchstart", dismiss);
      document.removeEventListener("mousedown", dismiss);
    };
  }, [show]);

  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={handleEnter}
      onMouseLeave={() => setShow(false)}
      onClick={handleClick}
      ref={ref}
    >
      {children || (
        <Info className="w-3.5 h-3.5 text-[var(--color-text-secondary)]/50 hover:text-[var(--color-text-secondary)] cursor-help transition-colors" />
      )}
      {show && (
        <div
          className={`fixed z-[100] ${wide ? "w-80" : "w-64"} px-3 py-2 text-xs leading-relaxed text-[var(--color-text-primary)] bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg shadow-lg pointer-events-none`}
          style={{
            left: `${coords.left}px`,
            transform: "translateX(-50%)",
            ...(coords.pos === "top"
              ? { bottom: `${window.innerHeight - coords.top}px` }
              : { top: `${coords.top}px` }),
          }}
        >
          {content ?? text}
        </div>
      )}
    </span>
  );
}

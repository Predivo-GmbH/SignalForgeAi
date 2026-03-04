import { useState, useRef, useCallback } from "react";
import { Info } from "lucide-react";

interface TooltipProps {
  text: string;
  /** When true, renders the default Info icon trigger (same as omitting children). */
  icon?: boolean;
  children?: React.ReactNode;
}

export function Tooltip({ text, children }: TooltipProps) {
  const [show, setShow] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0, pos: "bottom" as "top" | "bottom" });
  const ref = useRef<HTMLSpanElement>(null);

  const handleEnter = useCallback(() => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      // Show below if near top of viewport, otherwise above
      if (rect.top < 100) {
        setCoords({ x: centerX, y: rect.bottom + 8, pos: "bottom" });
      } else {
        setCoords({ x: centerX, y: rect.top - 8, pos: "top" });
      }
    }
    setShow(true);
  }, []);

  return (
    <span
      className="relative inline-flex items-center"
      onMouseEnter={handleEnter}
      onMouseLeave={() => setShow(false)}
      ref={ref}
    >
      {children || (
        <Info className="w-3.5 h-3.5 text-[var(--color-text-secondary)]/50 hover:text-[var(--color-text-secondary)] cursor-help transition-colors" />
      )}
      {show && (
        <div
          className="fixed z-[100] w-64 px-3 py-2 text-xs leading-relaxed text-[var(--color-text-primary)] bg-[var(--color-bg-elevated)] border border-[var(--color-border)] rounded-lg shadow-lg pointer-events-none"
          style={{
            left: `${coords.x}px`,
            transform: "translateX(-50%)",
            ...(coords.pos === "top"
              ? { bottom: `${window.innerHeight - coords.y}px` }
              : { top: `${coords.y}px` }),
          }}
        >
          {text}
        </div>
      )}
    </span>
  );
}

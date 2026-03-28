import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  size?: "md" | "lg";
  children: React.ReactNode;
}

export function Modal({ open, onClose, title, size = "md", children }: ModalProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  // Focus trap
  useEffect(() => {
    if (!open) return;

    previousFocusRef.current = document.activeElement as HTMLElement;

    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    const modal = modalRef.current;
    if (!modal) return;

    const focusableElements = modal.querySelectorAll(focusableSelector);
    (focusableElements[0] as HTMLElement)?.focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;

      // Re-query in case DOM changed
      const currentFocusable = modal.querySelectorAll(focusableSelector);
      const first = currentFocusable[0] as HTMLElement;
      const last = currentFocusable[currentFocusable.length - 1] as HTMLElement;

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };

    modal.addEventListener("keydown", handleKeyDown);
    return () => {
      modal.removeEventListener("keydown", handleKeyDown);
      previousFocusRef.current?.focus();
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`relative w-full ${size === "lg" ? "max-w-2xl" : "max-w-md"} mx-4 max-h-[90vh] flex flex-col bg-(--color-bg-surface) border border-(--color-border) rounded-xl shadow-2xl`}
      >
        <div className="flex items-center justify-between px-4 sm:px-5 py-3 sm:py-4 border-b border-(--color-border)">
          <h2 className="text-sm sm:text-base font-semibold text-(--color-text-primary) truncate mr-2">{title}</h2>
          <button
            onClick={onClose}
            className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg text-(--color-text-secondary) hover:text-(--color-text-primary) hover:bg-(--color-bg-elevated) transition-colors shrink-0"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" aria-hidden="true" />
          </button>
        </div>
        <div className="px-4 sm:px-5 py-3 sm:py-4 overflow-y-auto">{children}</div>
      </div>
    </div>,
    document.body,
  );
}

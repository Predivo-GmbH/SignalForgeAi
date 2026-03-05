import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/cn";
import { CRYPTO_LIST } from "@/lib/cryptoSymbols";
import type { CryptoEntry } from "@/lib/cryptoSymbols";

export function SymbolAutocomplete({
  value,
  onChange,
}: {
  value: string;
  onChange: (val: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [highlightIdx, setHighlightIdx] = useState(-1);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const query = value.trim().toUpperCase();

  const suggestions: CryptoEntry[] = useMemo(() => {
    if (!query) return [];
    return CRYPTO_LIST.filter(
      (c) =>
        c.symbol.includes(query) ||
        c.name.toUpperCase().includes(query),
    ).slice(0, 8);
  }, [query]);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Scroll highlighted item into view
  useEffect(() => {
    if (highlightIdx >= 0 && listRef.current) {
      const el = listRef.current.children[highlightIdx] as HTMLElement | undefined;
      el?.scrollIntoView({ block: "nearest" });
    }
  }, [highlightIdx]);

  const selectItem = useCallback(
    (entry: CryptoEntry) => {
      onChange(entry.symbol);
      setOpen(false);
      setHighlightIdx(-1);
    },
    [onChange],
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIdx((i) => (i + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIdx((i) => (i <= 0 ? suggestions.length - 1 : i - 1));
    } else if (e.key === "Enter" && highlightIdx >= 0) {
      e.preventDefault();
      selectItem(suggestions[highlightIdx]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  const showDropdown = open && query.length > 0 && suggestions.length > 0;
  // Check for exact match to hide dropdown when symbol is already selected
  const exactMatch = suggestions.length === 1 && suggestions[0].symbol === query;

  return (
    <div ref={wrapperRef} className="relative">
      <input
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
          setHighlightIdx(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        placeholder="BTC"
        autoComplete="off"
        className="w-full bg-(--color-bg-surface) border border-(--color-border) rounded-lg px-2.5 py-1.5 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
      />
      {showDropdown && !exactMatch && (
        <div
          ref={listRef}
          className="absolute z-50 left-0 right-0 top-full mt-1 max-h-48 overflow-y-auto bg-(--color-bg-surface) border border-(--color-border) rounded-lg shadow-lg py-1"
        >
          {suggestions.map((entry, i) => (
            <button
              key={entry.symbol}
              type="button"
              onMouseDown={(e) => e.preventDefault()}
              onClick={() => selectItem(entry)}
              onMouseEnter={() => setHighlightIdx(i)}
              className={cn(
                "w-full flex items-center gap-2 px-2.5 py-1.5 text-left transition-colors",
                i === highlightIdx
                  ? "bg-(--color-accent)/10"
                  : "hover:bg-(--color-bg-elevated)",
              )}
            >
              <span className="text-xs font-bold font-mono text-(--color-text-primary) w-14 shrink-0">
                {entry.symbol}
              </span>
              <span className="text-xs text-(--color-text-secondary) truncate">
                {entry.name}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

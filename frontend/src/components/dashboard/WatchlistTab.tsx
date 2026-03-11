import { useState, useMemo } from "react";
import {
  Loader2, Eye, Sparkles, Wallet, Globe, Clock,
  Search, ChevronDown, ChevronRight, X, RotateCcw, Zap, Ban,
} from "lucide-react";
import { Tooltip } from "@/components/ui/Tooltip";
import {
  useWatchlist,
  useRemoveWatchlistSymbol,
  useRemoveCandidate,
  useUnblockCandidate,
  useTriggerDiscovery,
  type WatchlistSymbol,
} from "@/hooks/useWatchlist";

type SourceFilter = "all" | WatchlistSymbol["source"];

const SOURCE_CONFIG: Record<
  WatchlistSymbol["source"],
  { label: string; dot: string; icon: typeof Sparkles }
> = {
  ai_deploy: {
    label: "AI Advisor",
    dot: "bg-[var(--color-accent)]",
    icon: Sparkles,
  },
  portfolio_sync: {
    label: "Portfolio",
    dot: "bg-[var(--color-positive)]",
    icon: Wallet,
  },
  universe_discovery: {
    label: "AI Curated",
    dot: "bg-[var(--color-warning,#f59e0b)]",
    icon: Globe,
  },
};

const FILTER_TABS: { key: SourceFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "portfolio_sync", label: "Portfolio" },
  { key: "ai_deploy", label: "AI Advisor" },
  { key: "universe_discovery", label: "AI Curated" },
];

export function WatchlistTab() {
  const { data, isLoading, isError } = useWatchlist();
  const triggerDiscovery = useTriggerDiscovery();
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [candidatesOpen, setCandidatesOpen] = useState(false);
  const [blocklistOpen, setBlocklistOpen] = useState(false);
  const [discoveryQueued, setDiscoveryQueued] = useState(false);

  const counts = useMemo(() => {
    if (!data) return { all: 0, ai_deploy: 0, portfolio_sync: 0, universe_discovery: 0 };
    return {
      all: data.strategy_symbols.length,
      ai_deploy: data.strategy_symbols.filter((s) => s.source === "ai_deploy").length,
      portfolio_sync: data.strategy_symbols.filter((s) => s.source === "portfolio_sync").length,
      universe_discovery: data.strategy_symbols.filter((s) => s.source === "universe_discovery").length,
    };
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.strategy_symbols.filter((s) => {
      const matchesSource = sourceFilter === "all" || s.source === sourceFilter;
      const matchesSearch = !search || s.symbol.toLowerCase().includes(search.toLowerCase());
      return matchesSource && matchesSearch;
    });
  }, [data, sourceFilter, search]);

  const filteredCandidates = useMemo(() => {
    if (!data) return [];
    if (!search) return data.candidate_pool;
    return data.candidate_pool.filter((s) => s.toLowerCase().includes(search.toLowerCase()));
  }, [data, search]);

  const filteredBlocklist = useMemo(() => {
    if (!data) return [];
    if (!search) return data.blocklist;
    return data.blocklist.filter((s) => s.toLowerCase().includes(search.toLowerCase()));
  }, [data, search]);

  function handleDiscovery() {
    setDiscoveryQueued(true);
    triggerDiscovery.mutate(undefined, {
      onSettled: () => setTimeout(() => setDiscoveryQueued(false), 5000),
    });
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-[var(--color-accent)]" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <p className="text-center text-sm text-[var(--color-text-secondary)] py-12">
        Could not load watchlist.
      </p>
    );
  }

  const hasSymbols = data.strategy_symbols.length > 0;
  const hasCandidates = data.candidate_pool.length > 0;
  const hasBlocklist = data.blocklist.length > 0;

  return (
    <div className="space-y-3">
      {/* Header + discover button */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Eye className="w-3.5 h-3.5 text-[var(--color-accent)]" />
          <Tooltip text="All symbols the pipeline actively monitors. Portfolio holdings are always included. AI-curated symbols join after building candle history.">
            <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider cursor-help">
              Active Watchlist
            </span>
          </Tooltip>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-[var(--color-text-secondary)] tabular-nums">
            {data.total_strategy_symbols} symbol{data.total_strategy_symbols !== 1 ? "s" : ""}
          </span>
          <Tooltip text="Scan all connected exchanges now — AI evaluates and adds qualifying pairs immediately.">
            <button
              onClick={handleDiscovery}
              disabled={discoveryQueued || triggerDiscovery.isPending}
              className="inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] px-2 py-0.5 text-[11px] font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-accent)] hover:border-[var(--color-accent)]/40 transition-colors disabled:opacity-50"
            >
              {discoveryQueued ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Zap className="w-3 h-3" />
              )}
              {discoveryQueued ? "Queued…" : "Discover now"}
            </button>
          </Tooltip>
        </div>
      </div>

      {!hasSymbols ? (
        <p className="text-sm text-[var(--color-text-secondary)] text-center py-6">
          No active strategy. Deploy one via the AI Advisor.
        </p>
      ) : (
        <>
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--color-text-secondary)] pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter symbols…"
              className="w-full rounded-lg bg-[var(--color-bg-elevated)] border border-[var(--color-border)] pl-8 pr-3 py-1.5 text-xs text-[var(--color-text-primary)] placeholder:text-[var(--color-text-secondary)] focus:outline-none focus:border-[var(--color-accent)] transition-colors"
            />
          </div>

          {/* Source filter tabs */}
          <div className="flex gap-1 flex-wrap">
            {FILTER_TABS.map(({ key, label }) => {
              const count = counts[key];
              const active = sourceFilter === key;
              return (
                <button
                  key={key}
                  onClick={() => setSourceFilter(key)}
                  className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[11px] font-medium transition-colors ${
                    active
                      ? "bg-[var(--color-accent)] text-white"
                      : "bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]"
                  }`}
                >
                  {key !== "all" && (
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${active ? "bg-white/70" : SOURCE_CONFIG[key as WatchlistSymbol["source"]].dot}`}
                    />
                  )}
                  {label}
                  <span className={`tabular-nums ${active ? "opacity-80" : "opacity-60"}`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Symbol chips */}
          {filtered.length === 0 ? (
            <p className="text-xs text-[var(--color-text-secondary)] text-center py-4 opacity-60">
              No symbols match.
            </p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {filtered.map((item) => (
                <SymbolChip key={item.symbol} item={item} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Candidate pool */}
      {hasCandidates && (
        <div className="border-t border-[var(--color-border)] pt-3">
          <button
            className="flex items-center justify-between w-full mb-2 group"
            onClick={() => setCandidatesOpen((o) => !o)}
          >
            <div className="flex items-center gap-2">
              <Clock className="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
              <Tooltip text="AI-approved symbols building candle history. Once they have 300+ candles on the primary timeframe, they're promoted to the active watchlist automatically — usually within minutes of discovery.">
                <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider cursor-pointer group-hover:text-[var(--color-text-primary)] transition-colors">
                  Building History
                </span>
              </Tooltip>
              <span className="text-xs text-[var(--color-text-secondary)] tabular-nums opacity-60">
                {data.total_candidates}
              </span>
            </div>
            {candidatesOpen ? (
              <ChevronDown className="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
            )}
          </button>

          {candidatesOpen && (
            <div className="flex flex-wrap gap-1.5">
              {filteredCandidates.map((sym) => (
                <CandidateChip key={sym} symbol={sym} />
              ))}
              {filteredCandidates.length === 0 && (
                <p className="text-xs text-[var(--color-text-secondary)] opacity-60">No matches.</p>
              )}
            </div>
          )}
          {!candidatesOpen && (
            <p className="text-[11px] text-[var(--color-text-secondary)] opacity-60">
              AI-vetted — will be promoted automatically once candles are ready.
            </p>
          )}
        </div>
      )}

      {/* Blocklist */}
      {hasBlocklist && (
        <div className="border-t border-[var(--color-border)] pt-3">
          <button
            className="flex items-center justify-between w-full mb-2 group"
            onClick={() => setBlocklistOpen((o) => !o)}
          >
            <div className="flex items-center gap-2">
              <Ban className="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
              <Tooltip text="Symbols you removed from the candidate pool. Auto-discovery will not re-add these. Click the undo icon to unblock.">
                <span className="text-xs font-semibold text-[var(--color-text-secondary)] uppercase tracking-wider cursor-pointer group-hover:text-[var(--color-text-primary)] transition-colors">
                  Blocked
                </span>
              </Tooltip>
              <span className="text-xs text-[var(--color-text-secondary)] tabular-nums opacity-60">
                {data.blocklist.length}
              </span>
            </div>
            {blocklistOpen ? (
              <ChevronDown className="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-[var(--color-text-secondary)]" />
            )}
          </button>

          {blocklistOpen && (
            <div className="flex flex-wrap gap-1.5">
              {filteredBlocklist.map((sym) => (
                <BlockedChip key={sym} symbol={sym} />
              ))}
            </div>
          )}
        </div>
      )}

      {!hasSymbols && !hasCandidates && (
        <p className="text-center text-xs text-[var(--color-text-secondary)] opacity-60 pb-2">
          Universe expansion runs every 6 hours. Portfolio sync runs every 5 minutes.
        </p>
      )}
    </div>
  );
}

function _timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const BLOCK_REASON_LABELS: Record<string, string> = {
  no_trend: "No trend detected",
  chaotic_regime: "Chaotic market regime",
  low_confluence: "Confluence below threshold",
  mtf_filter: "Higher-timeframe contradiction",
  position_filter: "Position already open",
  ai_reject: "AI rejected signal",
  dedup: "Duplicate signal",
  error: "Pipeline error",
};

const SOURCE_DESCRIPTIONS: Record<WatchlistSymbol["source"], (item: WatchlistSymbol) => string> = {
  portfolio_sync: (item) =>
    `You hold ${item.symbol.split("/")[0]}. Added automatically so the pipeline can generate SELL signals to protect your position in a downtrend.`,
  universe_discovery: () =>
    "AI-curated from universe expansion. Evaluated across all connected exchanges and approved for its market structure quality.",
  ai_deploy: () =>
    "Added by the AI Advisor when the strategy was deployed.",
};

function SymbolTooltipContent({ item }: { item: WatchlistSymbol }) {
  const cfg = SOURCE_CONFIG[item.source] ?? SOURCE_CONFIG.ai_deploy;
  const Icon = cfg.icon;
  const s = item.last_status;

  const statusColor =
    !s ? "text-[var(--color-text-secondary)]"
    : s.block_reason ? "text-[var(--color-warning,#f59e0b)]"
    : s.action === "BUY" || s.action === "SELL" ? "text-[var(--color-positive)]"
    : "text-[var(--color-text-secondary)]";

  const statusText =
    !s ? "No pipeline data yet"
    : s.block_reason ? (BLOCK_REASON_LABELS[s.block_reason] ?? s.block_reason)
    : s.action === "NO_TRADE" ? "Passed all filters — no signal generated"
    : `${s.action} signal generated`;

  return (
    <div className="space-y-2">
      {/* Source header */}
      <div className="flex items-center gap-1.5 font-semibold">
        <span className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />
        <Icon className="w-3.5 h-3.5" />
        <span>{cfg.label}</span>
      </div>
      {/* Why it's here */}
      <p className="text-[var(--color-text-secondary)] leading-snug">
        {SOURCE_DESCRIPTIONS[item.source](item)}
      </p>
      {/* Divider */}
      <div className="border-t border-[var(--color-border)]" />
      {/* Pipeline status */}
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-2">
          <span className="text-[var(--color-text-secondary)]">Last check</span>
          <span className="tabular-nums">{s ? _timeAgo(s.checked_at) : "—"}</span>
        </div>
        {s?.regime && (
          <div className="flex items-center justify-between gap-2">
            <span className="text-[var(--color-text-secondary)]">Regime</span>
            <span className="capitalize">{s.regime.replace(/_/g, " ")}</span>
          </div>
        )}
        {s?.confluence_score != null && (
          <div className="flex items-center justify-between gap-2">
            <span className="text-[var(--color-text-secondary)]">Confluence</span>
            <span className="tabular-nums">{s.confluence_score}</span>
          </div>
        )}
        <div className="flex items-start justify-between gap-2">
          <span className="text-[var(--color-text-secondary)] shrink-0">Status</span>
          <span className={`text-right ${statusColor}`}>{statusText}</span>
        </div>
      </div>
    </div>
  );
}

function SymbolChip({ item }: { item: WatchlistSymbol }) {
  const cfg = SOURCE_CONFIG[item.source] ?? SOURCE_CONFIG.ai_deploy;
  const remove = useRemoveWatchlistSymbol();
  const canRemove = item.source === "universe_discovery";

  return (
    <span className={`inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:border-[var(--color-accent)]/40 ${canRemove ? "pl-2.5 pr-1.5" : "px-2.5"} py-1`}>
      <Tooltip content={<SymbolTooltipContent item={item} />} wide>
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 cursor-help ${cfg.dot}`} />
      </Tooltip>
      {item.symbol}
      {canRemove && (
        <Tooltip text="Remove and block — won't be re-added by auto-discovery">
          <button
            onClick={() => remove.mutate(item.symbol)}
            disabled={remove.isPending}
            className="rounded-full p-0.5 hover:bg-red-500/20 hover:text-red-400 transition-colors disabled:opacity-40"
          >
            <X className="w-3 h-3" />
          </button>
        </Tooltip>
      )}
    </span>
  );
}

function CandidateChip({ symbol }: { symbol: string }) {
  const remove = useRemoveCandidate();

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] pl-2.5 pr-1.5 py-1 text-xs font-medium text-[var(--color-text-secondary)]">
      {symbol}
      <Tooltip text="Remove and block — won't be re-added by auto-discovery">
        <button
          onClick={() => remove.mutate(symbol)}
          disabled={remove.isPending}
          className="rounded-full p-0.5 hover:bg-red-500/20 hover:text-red-400 transition-colors disabled:opacity-40"
        >
          <X className="w-3 h-3" />
        </button>
      </Tooltip>
    </span>
  );
}

function BlockedChip({ symbol }: { symbol: string }) {
  const unblock = useUnblockCandidate();

  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[var(--color-bg-elevated)] border border-[var(--color-border)] pl-2.5 pr-1.5 py-1 text-xs font-medium text-[var(--color-text-secondary)] opacity-60">
      {symbol}
      <Tooltip text="Unblock — allow auto-discovery to add this again">
        <button
          onClick={() => unblock.mutate(symbol)}
          disabled={unblock.isPending}
          className="rounded-full p-0.5 hover:bg-[var(--color-accent)]/20 hover:text-[var(--color-accent)] transition-colors disabled:opacity-40"
        >
          <RotateCcw className="w-3 h-3" />
        </button>
      </Tooltip>
    </span>
  );
}

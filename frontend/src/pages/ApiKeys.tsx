import { useState } from "react";
import { Eye, EyeOff, Shield, ExternalLink } from "lucide-react";
import { cn } from "@/lib/cn";

interface BrokerConfig {
  name: string;
  description: string;
  color: string;
  fields: { key: string; label: string }[];
  docsUrl: string;
}

const BROKERS: BrokerConfig[] = [
  {
    name: "Alpaca",
    description: "Commission-free stock & crypto trading API",
    color: "text-yellow-500",
    fields: [
      { key: "apiKey", label: "API Key" },
      { key: "apiSecret", label: "API Secret" },
    ],
    docsUrl: "https://docs.alpaca.markets/",
  },
  {
    name: "Binance",
    description: "Crypto exchange with spot & futures trading",
    color: "text-amber-400",
    fields: [
      { key: "apiKey", label: "API Key" },
      { key: "apiSecret", label: "API Secret" },
    ],
    docsUrl: "https://binance-docs.github.io/apidocs/",
  },
];

interface BrokerState {
  [field: string]: string;
  mode: "paper" | "live";
}

function BrokerCard({ broker }: { broker: BrokerConfig }) {
  const [state, setState] = useState<BrokerState>(() => {
    const initial: BrokerState = { mode: "paper" };
    for (const field of broker.fields) {
      initial[field.key] = "";
    }
    return initial;
  });
  const [showSecrets, setShowSecrets] = useState<Record<string, boolean>>({});

  function toggleVisible(key: string) {
    setShowSecrets((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function maskValue(value: string): string {
    if (!value) return "";
    if (value.length <= 8) return "****";
    return value.slice(0, 4) + "****" + value.slice(-4);
  }

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-(--color-bg-elevated) rounded-lg flex items-center justify-center">
            <Shield className={cn("w-5 h-5", broker.color)} />
          </div>
          <div>
            <h3 className="text-base font-semibold text-(--color-text-primary)">
              {broker.name}
            </h3>
            <p className="text-xs text-(--color-text-secondary)">
              {broker.description}
            </p>
          </div>
        </div>
        <a
          href={broker.docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-(--color-accent) hover:underline"
        >
          Docs
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Fields */}
      <div className="space-y-3">
        {broker.fields.map((field) => (
          <div key={field.key} className="space-y-1.5">
            <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
              {field.label}
            </label>
            <div className="relative">
              <input
                type={showSecrets[field.key] ? "text" : "password"}
                value={
                  showSecrets[field.key]
                    ? state[field.key]
                    : maskValue(state[field.key])
                }
                onChange={(e) =>
                  setState((prev) => ({
                    ...prev,
                    [field.key]: e.target.value,
                  }))
                }
                placeholder={`Enter ${field.label.toLowerCase()}`}
                className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 pr-10 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
              />
              <button
                type="button"
                onClick={() => toggleVisible(field.key)}
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-(--color-bg-surface) rounded transition-colors"
              >
                {showSecrets[field.key] ? (
                  <EyeOff className="w-4 h-4 text-(--color-text-secondary)" />
                ) : (
                  <Eye className="w-4 h-4 text-(--color-text-secondary)" />
                )}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Mode toggle */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Mode
        </span>
        <div className="flex bg-(--color-bg-elevated) rounded-lg p-0.5">
          <button
            onClick={() => setState((prev) => ({ ...prev, mode: "paper" }))}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-colors",
              state.mode === "paper"
                ? "bg-(--color-accent) text-white"
                : "text-(--color-text-secondary) hover:text-(--color-text-primary)"
            )}
          >
            Paper
          </button>
          <button
            onClick={() => setState((prev) => ({ ...prev, mode: "live" }))}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-colors",
              state.mode === "live"
                ? "bg-(--color-negative) text-white"
                : "text-(--color-text-secondary) hover:text-(--color-text-primary)"
            )}
          >
            Live
          </button>
        </div>
      </div>
    </div>
  );
}

/* ----- Main Page ----- */
export function ApiKeysPage() {
  return (
    <div className="p-6 space-y-6 max-w-[900px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          API Keys & Broker Connections
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Manage exchange credentials and trading mode
        </p>
      </div>

      {/* Broker cards */}
      <div className="grid gap-6">
        {BROKERS.map((broker) => (
          <BrokerCard key={broker.name} broker={broker} />
        ))}
      </div>

      {/* Phase 5 note */}
      <div className="bg-(--color-bg-elevated)/50 border border-(--color-border) rounded-xl p-4 text-center">
        <p className="text-xs text-(--color-text-secondary)">
          Backend broker CRUD coming in Phase 5 &mdash; credentials will be
          encrypted and stored server-side
        </p>
      </div>
    </div>
  );
}

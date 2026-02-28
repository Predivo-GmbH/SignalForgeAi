import { useState } from "react";
import {
  Shield,
  ExternalLink,
  Plus,
  X,
  Loader2,
  Trash2,
  Wifi,
  WifiOff,
} from "lucide-react";
import { cn } from "@/lib/cn";
import {
  useBrokerConnections,
  useConnectBroker,
  useDisconnectBroker,
} from "@/hooks/useBrokerConnections";
import type { ConnectBrokerRequest } from "@/hooks/useBrokerConnections";

/* ---- Broker metadata ---- */

interface BrokerMeta {
  name: string;
  description: string;
  docsUrl: string;
}

const SUPPORTED_BROKERS: BrokerMeta[] = [
  {
    name: "Alpaca",
    description: "Commission-free stock & crypto trading API",
    docsUrl: "https://docs.alpaca.markets/",
  },
  {
    name: "Binance",
    description: "Crypto exchange with spot & futures trading",
    docsUrl: "https://binance-docs.github.io/apidocs/",
  },
];

/* ---- Connect Form ---- */

function ConnectForm({ onClose }: { onClose: () => void }) {
  const connect = useConnectBroker();

  const [broker, setBroker] = useState(SUPPORTED_BROKERS[0].name);
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [isPaper, setIsPaper] = useState(true);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: ConnectBrokerRequest = {
      broker: broker.toLowerCase(),
      api_key: apiKey,
      api_secret: apiSecret,
      is_paper: isPaper,
    };
    connect.mutate(payload, { onSuccess: () => onClose() });
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4"
    >
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-(--color-text-primary)">
          Connect Broker
        </h3>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded hover:bg-(--color-bg-elevated) transition-colors"
        >
          <X className="w-4 h-4 text-(--color-text-secondary)" />
        </button>
      </div>

      {/* Broker selector */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Broker
        </label>
        <select
          value={broker}
          onChange={(e) => setBroker(e.target.value)}
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        >
          {SUPPORTED_BROKERS.map((b) => (
            <option key={b.name} value={b.name}>
              {b.name}
            </option>
          ))}
        </select>
      </div>

      {/* API Key */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          API Key
        </label>
        <input
          type="password"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          placeholder="Enter API key"
          required
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        />
      </div>

      {/* API Secret */}
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          API Secret
        </label>
        <input
          type="password"
          value={apiSecret}
          onChange={(e) => setApiSecret(e.target.value)}
          placeholder="Enter API secret"
          required
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        />
      </div>

      {/* Paper / Live toggle */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Mode
        </span>
        <div className="flex bg-(--color-bg-elevated) rounded-lg p-0.5">
          <button
            type="button"
            onClick={() => setIsPaper(true)}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-colors",
              isPaper
                ? "bg-(--color-accent) text-white"
                : "text-(--color-text-secondary) hover:text-(--color-text-primary)",
            )}
          >
            Paper
          </button>
          <button
            type="button"
            onClick={() => setIsPaper(false)}
            className={cn(
              "px-3 py-1 rounded-md text-xs font-medium transition-colors",
              !isPaper
                ? "bg-(--color-negative) text-white"
                : "text-(--color-text-secondary) hover:text-(--color-text-primary)",
            )}
          >
            Live
          </button>
        </div>
      </div>

      {/* Error */}
      {connect.isError && (
        <p className="text-xs text-(--color-negative)">
          {connect.error instanceof Error
            ? connect.error.message
            : "Failed to connect broker"}
        </p>
      )}

      {/* Submit */}
      <button
        type="submit"
        disabled={connect.isPending}
        className="w-full flex items-center justify-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-sm font-medium rounded-lg px-4 py-2.5 transition-colors disabled:opacity-50"
      >
        {connect.isPending ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Shield className="w-4 h-4" />
        )}
        {connect.isPending ? "Connecting..." : "Connect"}
      </button>
    </form>
  );
}

/* ---- Connection Card ---- */

function ConnectionCard({
  id,
  broker,
  apiKeyMasked,
  isPaper,
}: {
  id: string;
  broker: string;
  apiKeyMasked: string;
  isPaper: boolean;
}) {
  const disconnect = useDisconnectBroker();
  const meta = SUPPORTED_BROKERS.find(
    (b) => b.name.toLowerCase() === broker.toLowerCase(),
  );

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-(--color-bg-elevated) rounded-lg flex items-center justify-center">
            <Wifi className="w-5 h-5 text-(--color-positive)" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-(--color-text-primary) capitalize">
              {broker}
            </h3>
            {meta && (
              <p className="text-xs text-(--color-text-secondary)">
                {meta.description}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {meta && (
            <a
              href={meta.docsUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 text-xs text-(--color-accent) hover:underline"
            >
              Docs
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>

      {/* Info row */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <span className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            API Key
          </span>
          <span className="text-sm font-mono text-(--color-text-primary)">
            {apiKeyMasked}
          </span>
        </div>

        <span
          className={cn(
            "px-2.5 py-1 rounded-full text-xs font-medium",
            isPaper
              ? "bg-(--color-accent-soft) text-(--color-accent)"
              : "bg-(--color-negative)/10 text-(--color-negative)",
          )}
        >
          {isPaper ? "Paper" : "Live"}
        </span>
      </div>

      {/* Disconnect */}
      <button
        onClick={() => disconnect.mutate(id)}
        disabled={disconnect.isPending}
        className="flex items-center gap-2 text-xs font-medium text-(--color-negative) hover:text-(--color-negative)/80 transition-colors disabled:opacity-50"
      >
        {disconnect.isPending ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : (
          <Trash2 className="w-3.5 h-3.5" />
        )}
        {disconnect.isPending ? "Disconnecting..." : "Disconnect"}
      </button>
    </div>
  );
}

/* ---- Main Page ---- */

export function ApiKeysPage() {
  const { data: connections, isLoading, isError, error } = useBrokerConnections();
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="p-6 space-y-6 max-w-[900px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-(--color-text-primary)">
            API Connections
          </h1>
          <p className="text-sm text-(--color-text-secondary) mt-1">
            Manage exchange credentials and trading mode
          </p>
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-sm font-medium rounded-lg px-4 py-2 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Connect Broker
          </button>
        )}
      </div>

      {/* Connect form */}
      {showForm && <ConnectForm onClose={() => setShowForm(false)} />}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-(--color-negative)/10 border border-(--color-negative)/20 rounded-xl p-4 text-center">
          <p className="text-sm text-(--color-negative)">
            {error instanceof Error
              ? error.message
              : "Failed to load connections"}
          </p>
        </div>
      )}

      {/* Connection cards */}
      {connections && connections.length > 0 && (
        <div className="grid gap-6">
          {connections.map((conn) => (
            <ConnectionCard
              key={conn.id}
              id={conn.id}
              broker={conn.broker}
              apiKeyMasked={conn.api_key_masked}
              isPaper={conn.is_paper}
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {connections && connections.length === 0 && !showForm && (
        <div className="bg-(--color-bg-elevated)/50 border border-(--color-border) rounded-xl p-8 text-center space-y-3">
          <WifiOff className="w-8 h-8 text-(--color-text-secondary) mx-auto" />
          <p className="text-sm text-(--color-text-secondary)">
            No broker connections yet. Connect a broker to start trading.
          </p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-2 text-sm font-medium text-(--color-accent) hover:underline"
          >
            <Plus className="w-4 h-4" />
            Add your first connection
          </button>
        </div>
      )}
    </div>
  );
}

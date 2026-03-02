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
  Bell,
  Save,
  DollarSign,
} from "lucide-react";
import { cn } from "@/lib/cn";
import {
  useBrokerConnections,
  useConnectBroker,
  useDisconnectBroker,
} from "@/hooks/useBrokerConnections";
import { useAlertConfig, useUpdateAlertConfig } from "@/hooks/useAlertConfig";
import type { ConnectBrokerRequest } from "@/hooks/useBrokerConnections";
import type { AlertConfig } from "@/hooks/useAlertConfig";
import { AiUsageTab } from "@/components/settings/AiUsageTab";

type Tab = "connections" | "alerts" | "ai-usage";

/* ---- Broker metadata ---- */

interface BrokerMeta {
  name: string;
  description: string;
  docsUrl: string;
}

const SUPPORTED_BROKERS: BrokerMeta[] = [
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

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: ConnectBrokerRequest = {
      broker: broker.toLowerCase(),
      api_key: apiKey,
      api_secret: apiSecret,
      is_paper: false,
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

      {connect.isError && (
        <p className="text-xs text-(--color-negative)">
          {connect.error instanceof Error
            ? connect.error.message
            : "Failed to connect broker"}
        </p>
      )}

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
}: {
  id: string;
  broker: string;
  apiKeyMasked: string;
}) {
  const disconnect = useDisconnectBroker();
  const meta = SUPPORTED_BROKERS.find(
    (b) => b.name.toLowerCase() === broker.toLowerCase(),
  );

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
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

      <div className="space-y-1">
        <span className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          API Key
        </span>
        <span className="text-sm font-mono text-(--color-text-primary)">
          {apiKeyMasked}
        </span>
      </div>

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

/* ---- Connections Tab ---- */

function ConnectionsTab() {
  const { data: connections, isLoading, isError, error } = useBrokerConnections();
  const [showForm, setShowForm] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-(--color-text-primary)">
            Broker Connections
          </h2>
          <p className="text-sm text-(--color-text-secondary) mt-0.5">
            Connect exchange API keys for live trading
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

      {showForm && <ConnectForm onClose={() => setShowForm(false)} />}

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
        </div>
      )}

      {isError && (
        <div className="bg-(--color-negative)/10 border border-(--color-negative)/20 rounded-xl p-4 text-center">
          <p className="text-sm text-(--color-negative)">
            {error instanceof Error ? error.message : "Failed to load connections"}
          </p>
        </div>
      )}

      {connections && connections.length > 0 && (
        <div className="grid gap-6">
          {connections.map((conn) => (
            <ConnectionCard
              key={conn.id}
              id={conn.id}
              broker={conn.broker}
              apiKeyMasked={conn.api_key_masked}
            />
          ))}
        </div>
      )}

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

/* ---- Alerts Tab ---- */

function AlertsTab() {
  const { data: config, isLoading } = useAlertConfig();
  const updateMutation = useUpdateAlertConfig();

  const [form, setForm] = useState<AlertConfig | null>(null);

  // Initialize form when config loads
  const current = form ?? config ?? {
    email_on_signal: false,
    email_daily_summary: false,
    min_confluence_alert: 60,
    alert_email: "",
  };

  function handleSave() {
    updateMutation.mutate(current, {
      onSuccess: () => setForm(null),
    });
  }

  const isDirty = form !== null;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-(--color-text-primary)">
          Alert Preferences
        </h2>
        <p className="text-sm text-(--color-text-secondary) mt-0.5">
          Configure email notifications for signals and daily summaries
        </p>
      </div>

      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-5">
        {/* Alert email */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Alert Email
          </label>
          <input
            type="email"
            value={current.alert_email}
            onChange={(e) =>
              setForm({ ...current, alert_email: e.target.value })
            }
            placeholder="your@email.com"
            className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
        </div>

        {/* Toggles */}
        <div className="space-y-3">
          <label className="flex items-center justify-between">
            <div>
              <p className="text-sm text-(--color-text-primary)">Email on Signal</p>
              <p className="text-xs text-(--color-text-secondary)">
                Receive an email when a new trading signal is generated
              </p>
            </div>
            <button
              onClick={() =>
                setForm({ ...current, email_on_signal: !current.email_on_signal })
              }
              className={cn(
                "w-10 h-6 rounded-full transition-colors relative",
                current.email_on_signal ? "bg-(--color-accent)" : "bg-(--color-bg-elevated)",
              )}
            >
              <span
                className={cn(
                  "absolute top-1 w-4 h-4 rounded-full bg-white transition-transform",
                  current.email_on_signal ? "translate-x-5" : "translate-x-1",
                )}
              />
            </button>
          </label>

          <label className="flex items-center justify-between">
            <div>
              <p className="text-sm text-(--color-text-primary)">Daily Summary</p>
              <p className="text-xs text-(--color-text-secondary)">
                Receive a daily email summary of trades and performance
              </p>
            </div>
            <button
              onClick={() =>
                setForm({
                  ...current,
                  email_daily_summary: !current.email_daily_summary,
                })
              }
              className={cn(
                "w-10 h-6 rounded-full transition-colors relative",
                current.email_daily_summary ? "bg-(--color-accent)" : "bg-(--color-bg-elevated)",
              )}
            >
              <span
                className={cn(
                  "absolute top-1 w-4 h-4 rounded-full bg-white transition-transform",
                  current.email_daily_summary ? "translate-x-5" : "translate-x-1",
                )}
              />
            </button>
          </label>
        </div>

        {/* Min confluence */}
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Minimum Confluence for Alerts
          </label>
          <input
            type="number"
            min={0}
            max={100}
            value={current.min_confluence_alert}
            onChange={(e) =>
              setForm({
                ...current,
                min_confluence_alert: Math.max(0, Math.min(100, Number(e.target.value))),
              })
            }
            className="w-32 bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
          <p className="text-xs text-(--color-text-secondary)">
            Only send alerts for signals with confluence score above this threshold
          </p>
        </div>

        {/* Save button */}
        <button
          onClick={handleSave}
          disabled={!isDirty || updateMutation.isPending}
          className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-sm font-medium rounded-lg px-4 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {updateMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          {updateMutation.isPending ? "Saving..." : "Save Changes"}
        </button>

        {updateMutation.isSuccess && !isDirty && (
          <p className="text-xs text-(--color-positive)">Settings saved successfully.</p>
        )}

        {updateMutation.isError && (
          <p className="text-xs text-(--color-negative)">
            {updateMutation.error instanceof Error
              ? updateMutation.error.message
              : "Failed to save settings"}
          </p>
        )}
      </div>
    </div>
  );
}

/* ---- Main Page ---- */

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("connections");

  return (
    <div className="p-6 space-y-6 max-w-[900px] mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Settings
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          Manage broker connections, notifications, and AI usage
        </p>
      </div>

      {/* Tab bar */}
      <div className="border-b border-(--color-border)">
        <div className="flex gap-6">
          <button
            onClick={() => setActiveTab("connections")}
            className={cn(
              "pb-2.5 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5",
              activeTab === "connections"
                ? "border-(--color-accent) text-(--color-accent)"
                : "border-transparent text-(--color-text-secondary) hover:text-(--color-text-primary)",
            )}
          >
            <Wifi className="w-3.5 h-3.5" />
            Connections
          </button>
          <button
            onClick={() => setActiveTab("alerts")}
            className={cn(
              "pb-2.5 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5",
              activeTab === "alerts"
                ? "border-(--color-accent) text-(--color-accent)"
                : "border-transparent text-(--color-text-secondary) hover:text-(--color-text-primary)",
            )}
          >
            <Bell className="w-3.5 h-3.5" />
            Alerts
          </button>
          <button
            onClick={() => setActiveTab("ai-usage")}
            className={cn(
              "pb-2.5 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5",
              activeTab === "ai-usage"
                ? "border-(--color-accent) text-(--color-accent)"
                : "border-transparent text-(--color-text-secondary) hover:text-(--color-text-primary)",
            )}
          >
            <DollarSign className="w-3.5 h-3.5" />
            AI Usage
          </button>
        </div>
      </div>

      {/* Tab content */}
      {activeTab === "connections" && <ConnectionsTab />}
      {activeTab === "alerts" && <AlertsTab />}
      {activeTab === "ai-usage" && <AiUsageTab />}
    </div>
  );
}

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
  User,
  Mail,
  Calendar,
  CheckCircle2,
  KeyRound,
  LogOut,
  Eye,
  EyeOff,
  Pencil,
  Clock,
  AlertTriangle,
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
import { TwoFactorSetup } from "@/components/settings/TwoFactorSetup";
import { useProfile, useChangePassword, useChangeEmail } from "@/hooks/useProfile";
import { useAuth } from "@/lib/auth";

type Tab = "profile" | "connections" | "alerts" | "ai-usage";

/* ---- Broker metadata ---- */

interface BrokerMeta {
  name: string;
  ccxtId: string;
  description: string;
  docsUrl: string;
  needsPassphrase?: boolean;
  keyExpiryDays?: number;
}

const SUPPORTED_BROKERS: BrokerMeta[] = [
  {
    name: "Binance",
    ccxtId: "binance",
    description: "Crypto exchange with spot & futures trading",
    docsUrl: "https://binance-docs.github.io/apidocs/",
  },
  {
    name: "KuCoin",
    ccxtId: "kucoin",
    description: "Crypto exchange with spot, margin & futures",
    docsUrl: "https://www.kucoin.com/docs/beginners/introduction",
    needsPassphrase: true,
  },
  {
    name: "MEXC",
    ccxtId: "mexc",
    description: "Crypto exchange with spot & futures trading",
    docsUrl: "https://mexcdevelop.github.io/apidocs/",
    keyExpiryDays: 90,
  },
  {
    name: "Bitstamp",
    ccxtId: "bitstamp",
    description: "European crypto exchange — fiat on/off ramp",
    docsUrl: "https://www.bitstamp.net/api/",
  },
  {
    name: "Crypto.com",
    ccxtId: "cryptocom",
    description: "Crypto exchange with spot & derivatives",
    docsUrl: "https://exchange-docs.crypto.com/exchange/v1/rest-ws/index.html",
  },
  {
    name: "Kraken",
    ccxtId: "kraken",
    description: "Established crypto exchange with fiat support",
    docsUrl: "https://docs.kraken.com/api/",
  },
];

/* ---- Connect Form ---- */

function ConnectForm({ onClose }: { onClose: () => void }) {
  const connect = useConnectBroker();

  const [broker, setBroker] = useState(SUPPORTED_BROKERS[0].name);
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [apiPassphrase, setApiPassphrase] = useState("");
  const [isPaper, setIsPaper] = useState(false);
  const [purpose, setPurpose] = useState<"read" | "trade">("read");

  const selectedMeta = SUPPORTED_BROKERS.find((b) => b.name === broker);
  const showPassphrase = selectedMeta?.needsPassphrase && !isPaper;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload: ConnectBrokerRequest = {
      broker: selectedMeta?.ccxtId ?? broker.toLowerCase(),
      api_key: apiKey,
      api_secret: apiSecret,
      api_passphrase: apiPassphrase || undefined,
      is_paper: isPaper,
      purpose,
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

      {!isPaper && (
        <>
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

          {showPassphrase && (
            <div className="space-y-1.5">
              <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                API Passphrase
              </label>
              <input
                type="password"
                value={apiPassphrase}
                onChange={(e) => setApiPassphrase(e.target.value)}
                placeholder="Enter API passphrase"
                required
                className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm font-mono text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
              />
              <p className="text-[10px] text-(--color-text-secondary)">
                KuCoin requires a passphrase set during API key creation
              </p>
            </div>
          )}
        </>
      )}

      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={isPaper}
          onChange={(e) => {
            setIsPaper(e.target.checked);
            if (e.target.checked) setPurpose("read");
          }}
          className="w-4 h-4 rounded border border-(--color-border) bg-(--color-bg-elevated) accent-(--color-accent)"
        />
        <span className="text-sm text-(--color-text-primary)">Paper trading mode</span>
      </label>

      {!isPaper && (
        <div className="space-y-1.5">
          <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
            Key Purpose
          </label>
          <div className="flex gap-3">
            <label className={cn(
              "flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors",
              purpose === "read"
                ? "border-(--color-accent) bg-(--color-accent)/10"
                : "border-(--color-border) bg-(--color-bg-elevated) hover:border-(--color-text-secondary)/30",
            )}>
              <input
                type="radio"
                name="purpose"
                value="read"
                checked={purpose === "read"}
                onChange={() => setPurpose("read")}
                className="accent-(--color-accent)"
              />
              <div>
                <p className="text-sm text-(--color-text-primary)">Read Only</p>
                <p className="text-[10px] text-(--color-text-secondary)">Portfolio viewing</p>
              </div>
            </label>
            <label className={cn(
              "flex-1 flex items-center gap-2 px-3 py-2 rounded-lg border cursor-pointer transition-colors",
              purpose === "trade"
                ? "border-amber-500 bg-amber-500/10"
                : "border-(--color-border) bg-(--color-bg-elevated) hover:border-(--color-text-secondary)/30",
            )}>
              <input
                type="radio"
                name="purpose"
                value="trade"
                checked={purpose === "trade"}
                onChange={() => setPurpose("trade")}
                className="accent-amber-500"
              />
              <div>
                <p className="text-sm text-(--color-text-primary)">Trading</p>
                <p className="text-[10px] text-(--color-text-secondary)">Order execution</p>
              </div>
            </label>
          </div>
          {purpose === "trade" && (
            <p className="text-xs text-amber-400">
              Trading keys may require IP whitelisting on your exchange.
            </p>
          )}
          {selectedMeta?.keyExpiryDays && (
            <p className="text-xs text-amber-400">
              {selectedMeta.name} keys without IP binding expire after {selectedMeta.keyExpiryDays} days. Link an IP address on {selectedMeta.name} for permanent validity.
            </p>
          )}
        </div>
      )}

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

function KeyExpiryBadge({ createdAt, expiryDays }: { createdAt: string; expiryDays: number }) {
  const created = new Date(createdAt);
  const expiresAt = new Date(created.getTime() + expiryDays * 24 * 60 * 60 * 1000);
  const now = new Date();
  const daysLeft = Math.ceil((expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));

  if (daysLeft <= 0) {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-red-500/10 border border-red-500/20">
        <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
        <span className="text-xs font-medium text-red-400">Key expired — reconnect required</span>
      </div>
    );
  }

  const isWarning = daysLeft <= 14;
  const isCritical = daysLeft <= 7;

  return (
    <div className={cn(
      "flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border",
      isCritical
        ? "bg-red-500/10 border-red-500/20"
        : isWarning
          ? "bg-amber-500/10 border-amber-500/20"
          : "bg-(--color-bg-elevated) border-(--color-border)",
    )}>
      <Clock className={cn(
        "w-3.5 h-3.5",
        isCritical ? "text-red-400" : isWarning ? "text-amber-400" : "text-(--color-text-secondary)",
      )} />
      <span className={cn(
        "text-xs font-medium",
        isCritical ? "text-red-400" : isWarning ? "text-amber-400" : "text-(--color-text-secondary)",
      )}>
        {daysLeft} day{daysLeft !== 1 ? "s" : ""} remaining
      </span>
      <span className="text-[10px] text-(--color-text-secondary)">
        (no IP binding)
      </span>
    </div>
  );
}

function ConnectionCard({
  id,
  broker,
  apiKeyMasked,
  purpose,
  createdAt,
}: {
  id: string;
  broker: string;
  apiKeyMasked: string;
  purpose: "read" | "trade";
  createdAt: string;
}) {
  const disconnect = useDisconnectBroker();
  const meta = SUPPORTED_BROKERS.find(
    (b) => b.ccxtId === broker || b.name.toLowerCase() === broker.toLowerCase(),
  );

  return (
    <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-(--color-bg-elevated) rounded-lg flex items-center justify-center">
            <Wifi className="w-5 h-5 text-(--color-positive)" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-(--color-text-primary)">
                {meta?.name ?? broker}
              </h3>
              <span className={cn(
                "px-2 py-0.5 text-[10px] font-semibold uppercase rounded-full",
                purpose === "trade"
                  ? "bg-amber-500/15 text-amber-400"
                  : "bg-blue-500/15 text-blue-400",
              )}>
                {purpose === "trade" ? "Trading" : "Read Only"}
              </span>
            </div>
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

      {meta?.keyExpiryDays && createdAt && (
        <KeyExpiryBadge createdAt={createdAt} expiryDays={meta.keyExpiryDays} />
      )}

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
              purpose={conn.purpose}
              createdAt={conn.created_at}
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

/* ---- Profile Tab ---- */

function ChangePasswordForm() {
  const mutation = useChangePassword();
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const mismatch = confirmPw.length > 0 && newPw !== confirmPw;
  const tooShort = newPw.length > 0 && newPw.length < 8;
  const canSubmit = currentPw && newPw.length >= 8 && newPw === confirmPw && !mutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate(
      { current_password: currentPw, new_password: newPw },
      {
        onSuccess: () => {
          setCurrentPw("");
          setNewPw("");
          setConfirmPw("");
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Current Password
        </label>
        <div className="relative">
          <input
            type={showCurrent ? "text" : "password"}
            value={currentPw}
            onChange={(e) => setCurrentPw(e.target.value)}
            className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 pr-10 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
          <button
            type="button"
            onClick={() => setShowCurrent(!showCurrent)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-(--color-text-secondary) hover:text-(--color-text-primary)"
          >
            {showCurrent ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          New Password
        </label>
        <div className="relative">
          <input
            type={showNew ? "text" : "password"}
            value={newPw}
            onChange={(e) => setNewPw(e.target.value)}
            className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 pr-10 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
          />
          <button
            type="button"
            onClick={() => setShowNew(!showNew)}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-(--color-text-secondary) hover:text-(--color-text-primary)"
          >
            {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        </div>
        {tooShort && (
          <p className="text-xs text-(--color-warning)">Must be at least 8 characters</p>
        )}
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Confirm New Password
        </label>
        <input
          type="password"
          value={confirmPw}
          onChange={(e) => setConfirmPw(e.target.value)}
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        />
        {mismatch && (
          <p className="text-xs text-(--color-negative)">Passwords do not match</p>
        )}
      </div>

      {mutation.isError && (
        <p className="text-xs text-(--color-negative)">
          {mutation.error instanceof Error ? mutation.error.message : "Failed to change password"}
        </p>
      )}
      {mutation.isSuccess && (
        <p className="text-xs text-(--color-positive)">Password changed successfully.</p>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-sm font-medium rounded-lg px-4 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {mutation.isPending ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <KeyRound className="w-4 h-4" />
        )}
        {mutation.isPending ? "Updating..." : "Update Password"}
      </button>
    </form>
  );
}

function ChangeEmailForm({ currentEmail }: { currentEmail: string }) {
  const mutation = useChangeEmail();
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");

  const canSubmit =
    newEmail && newEmail !== currentEmail && password && !mutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate(
      { new_email: newEmail, password },
      {
        onSuccess: () => {
          setNewEmail("");
          setPassword("");
        },
      },
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          New Email
        </label>
        <input
          type="email"
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
          placeholder={currentEmail}
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        />
      </div>

      <div className="space-y-1.5">
        <label className="block text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
          Current Password
        </label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Confirm with your password"
          className="w-full bg-(--color-bg-elevated) border border-(--color-border) rounded-lg px-3 py-2 text-sm text-(--color-text-primary) focus:outline-none focus:ring-2 focus:ring-(--color-accent)/50"
        />
      </div>

      {mutation.isError && (
        <p className="text-xs text-(--color-negative)">
          {mutation.error instanceof Error ? mutation.error.message : "Failed to change email"}
        </p>
      )}
      {mutation.isSuccess && (
        <p className="text-xs text-(--color-positive)">Email updated successfully.</p>
      )}

      <button
        type="submit"
        disabled={!canSubmit}
        className="flex items-center gap-2 bg-(--color-accent) hover:bg-(--color-accent)/90 text-white text-sm font-medium rounded-lg px-4 py-2.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {mutation.isPending ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Mail className="w-4 h-4" />
        )}
        {mutation.isPending ? "Updating..." : "Update Email"}
      </button>
    </form>
  );
}

function ProfileTab() {
  const { data: profile, isLoading } = useProfile();
  const logout = useAuth((s) => s.logout);
  const [showEmailForm, setShowEmailForm] = useState(false);
  const [showPasswordForm, setShowPasswordForm] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  const memberSince = profile?.created_at
    ? new Date(profile.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "—";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-(--color-text-primary)">
          Profile
        </h2>
        <p className="text-sm text-(--color-text-secondary) mt-0.5">
          Your account information and security settings
        </p>
      </div>

      {/* Account Info */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-5">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-full bg-(--color-accent)/15 flex items-center justify-center">
            <span className="text-xl font-bold text-(--color-accent)">
              {profile?.email?.charAt(0).toUpperCase() ?? "?"}
            </span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-base font-semibold text-(--color-text-primary) truncate">
              {profile?.email ?? "—"}
            </p>
            <div className="flex items-center gap-1.5 mt-0.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-(--color-positive)" />
              <span className="text-xs text-(--color-positive)">Active account</span>
            </div>
          </div>
        </div>

        <div className="border-t border-(--color-border)" />

        <div className="grid gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-(--color-bg-elevated) flex items-center justify-center shrink-0">
              <Calendar className="w-4 h-4 text-(--color-text-secondary)" />
            </div>
            <div>
              <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                Member since
              </p>
              <p className="text-sm text-(--color-text-primary)">{memberSince}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-(--color-bg-elevated) flex items-center justify-center shrink-0">
              <Shield className="w-4 h-4 text-(--color-text-secondary)" />
            </div>
            <div className="min-w-0">
              <p className="text-xs font-medium text-(--color-text-secondary) uppercase tracking-wider">
                Account ID
              </p>
              <p className="text-sm font-mono text-(--color-text-primary) truncate">
                {profile?.id ?? "—"}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Change Email */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-(--color-bg-elevated) flex items-center justify-center">
              <Mail className="w-4 h-4 text-(--color-text-secondary)" />
            </div>
            <div>
              <p className="text-sm font-semibold text-(--color-text-primary)">Email Address</p>
              <p className="text-xs text-(--color-text-secondary)">{profile?.email ?? "—"}</p>
            </div>
          </div>
          <button
            onClick={() => setShowEmailForm(!showEmailForm)}
            className="flex items-center gap-1.5 text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
          >
            <Pencil className="w-3.5 h-3.5" />
            {showEmailForm ? "Cancel" : "Change"}
          </button>
        </div>
        {showEmailForm && (
          <>
            <div className="border-t border-(--color-border)" />
            <ChangeEmailForm currentEmail={profile?.email ?? ""} />
          </>
        )}
      </div>

      {/* Change Password */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-(--color-bg-elevated) flex items-center justify-center">
              <KeyRound className="w-4 h-4 text-(--color-text-secondary)" />
            </div>
            <div>
              <p className="text-sm font-semibold text-(--color-text-primary)">Password</p>
              <p className="text-xs text-(--color-text-secondary)">Last changed: unknown</p>
            </div>
          </div>
          <button
            onClick={() => setShowPasswordForm(!showPasswordForm)}
            className="flex items-center gap-1.5 text-xs font-medium text-(--color-accent) hover:text-(--color-accent)/80 transition-colors"
          >
            <Pencil className="w-3.5 h-3.5" />
            {showPasswordForm ? "Cancel" : "Change"}
          </button>
        </div>
        {showPasswordForm && (
          <>
            <div className="border-t border-(--color-border)" />
            <ChangePasswordForm />
          </>
        )}
      </div>

      {/* Two-Factor Authentication */}
      <TwoFactorSetup />

      {/* Logout */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-5">
        <button
          onClick={logout}
          className="flex items-center gap-2 text-sm font-medium text-(--color-negative) hover:text-(--color-negative)/80 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Log out of your account
        </button>
      </div>
    </div>
  );
}

/* ---- Main Page ---- */

export function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>("profile");

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
            onClick={() => setActiveTab("profile")}
            className={cn(
              "pb-2.5 text-sm font-medium transition-colors border-b-2 -mb-px flex items-center gap-1.5",
              activeTab === "profile"
                ? "border-(--color-accent) text-(--color-accent)"
                : "border-transparent text-(--color-text-secondary) hover:text-(--color-text-primary)",
            )}
          >
            <User className="w-3.5 h-3.5" />
            Profile
          </button>
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
      {activeTab === "profile" && <ProfileTab />}
      {activeTab === "connections" && <ConnectionsTab />}
      {activeTab === "alerts" && <AlertsTab />}
      {activeTab === "ai-usage" && <AiUsageTab />}
    </div>
  );
}

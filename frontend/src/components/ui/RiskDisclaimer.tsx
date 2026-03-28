export function RiskDisclaimer() {
  return (
    <div className="rounded-lg border border-(--color-warning)/20 bg-(--color-warning)/5 p-3 sm:p-4 text-sm text-(--color-warning)">
      <p className="font-medium">Risk Disclaimer</p>
      <p className="mt-1 text-(--color-warning)/70">
        Trading cryptocurrencies involves substantial risk of loss. Past performance does not guarantee
        future results. SignalForgeAI is a trading tool, not financial advice. Only trade with funds you
        can afford to lose.
      </p>
    </div>
  );
}

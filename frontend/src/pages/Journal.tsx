import { BookOpen, Brain, Tag, MessageSquare } from "lucide-react";

function FeaturePreview({
  icon: Icon,
  title,
  description,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-8 h-8 rounded-lg bg-(--color-accent-soft) flex items-center justify-center shrink-0 mt-0.5">
        <Icon className="w-4 h-4 text-(--color-accent)" />
      </div>
      <div>
        <p className="text-sm font-medium text-(--color-text-primary)">
          {title}
        </p>
        <p className="text-xs text-(--color-text-secondary) mt-0.5">
          {description}
        </p>
      </div>
    </div>
  );
}

export function JournalPage() {
  return (
    <div className="p-6 space-y-6 max-w-[900px] mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-(--color-text-primary)">
          Trade Journal
        </h1>
        <p className="text-sm text-(--color-text-secondary) mt-1">
          AI-powered trade analysis and review
        </p>
      </div>

      {/* Empty state card */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-12 text-center">
        <div className="w-16 h-16 rounded-2xl bg-(--color-accent-soft) flex items-center justify-center mx-auto mb-5">
          <BookOpen className="w-8 h-8 text-(--color-accent)" />
        </div>
        <h2 className="text-lg font-semibold text-(--color-text-primary) mb-2">
          AI-assisted trade review coming in Phase 5
        </h2>
        <p className="text-sm text-(--color-text-secondary) max-w-md mx-auto">
          Pattern recognition, trade annotations, and Claude Haiku analysis
        </p>
      </div>

      {/* Planned features */}
      <div className="bg-(--color-bg-surface) border border-(--color-border) rounded-xl p-6 space-y-5">
        <h3 className="text-sm font-semibold text-(--color-text-secondary) uppercase tracking-wider">
          Planned Features
        </h3>
        <div className="grid gap-4">
          <FeaturePreview
            icon={Brain}
            title="AI Pattern Recognition"
            description="Claude Haiku analyzes your trades to identify recurring patterns, mistakes, and winning setups"
          />
          <FeaturePreview
            icon={Tag}
            title="Trade Annotations"
            description="Tag trades with setups, emotions, and market conditions for structured review"
          />
          <FeaturePreview
            icon={MessageSquare}
            title="Natural Language Queries"
            description='Ask questions like "Show me my best EUR/USD trades" and get instant insights'
          />
        </div>
      </div>
    </div>
  );
}

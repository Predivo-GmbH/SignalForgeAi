import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { X, Loader2 } from "lucide-react";
import { api } from "@/lib/api";

interface HelpDrawerProps {
  open: boolean;
  onClose: () => void;
}

export function HelpDrawer({ open, onClose }: HelpDrawerProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["guide"],
    queryFn: () => api.get<{ content: string }>("/guide"),
    staleTime: 5 * 60 * 1000,
    enabled: open,
  });

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 z-40 bg-black/30 transition-opacity"
        onClick={onClose}
      />
      {/* Drawer */}
      <div className="fixed top-0 right-0 z-50 h-full w-full max-w-lg bg-(--color-bg-surface) border-l border-(--color-border) shadow-xl flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-(--color-border) shrink-0">
          <h2 className="text-sm font-semibold text-(--color-text-primary)">
            User Guide
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-(--color-bg-elevated) transition-colors"
          >
            <X className="w-4 h-4 text-(--color-text-secondary)" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5">
          {isLoading && (
            <div className="flex items-center justify-center min-h-[200px]">
              <Loader2 className="w-5 h-5 animate-spin text-(--color-accent)" />
            </div>
          )}

          {error && (
            <div className="rounded-lg border border-(--color-negative)/30 bg-(--color-negative)/10 px-4 py-3 space-y-1">
              <p className="text-sm font-semibold text-(--color-negative)">
                Failed to load guide
              </p>
              <p className="text-xs text-(--color-text-secondary)">
                The guide file could not be found on the server.
              </p>
            </div>
          )}

          {data?.content && (
            <div className="prose prose-invert prose-sm max-w-none
              [&_h1]:text-xl [&_h1]:font-bold [&_h1]:text-(--color-text-primary) [&_h1]:mb-3 [&_h1]:mt-6 [&_h1]:first:mt-0
              [&_h2]:text-lg [&_h2]:font-bold [&_h2]:text-(--color-text-primary) [&_h2]:mb-2 [&_h2]:mt-6 [&_h2]:pt-3 [&_h2]:border-t [&_h2]:border-(--color-border)
              [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-(--color-text-primary) [&_h3]:mb-2 [&_h3]:mt-4
              [&_p]:text-sm [&_p]:text-(--color-text-secondary) [&_p]:leading-relaxed [&_p]:mb-3
              [&_ul]:text-sm [&_ul]:text-(--color-text-secondary) [&_ul]:mb-3 [&_ul]:pl-5 [&_ul]:list-disc
              [&_ol]:text-sm [&_ol]:text-(--color-text-secondary) [&_ol]:mb-3 [&_ol]:pl-5 [&_ol]:list-decimal
              [&_li]:mb-1 [&_li]:leading-relaxed
              [&_strong]:text-(--color-text-primary) [&_strong]:font-semibold
              [&_code]:text-xs [&_code]:bg-(--color-bg-elevated) [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:font-mono [&_code]:text-(--color-accent)
              [&_pre]:bg-(--color-bg-elevated) [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:mb-3 [&_pre]:overflow-x-auto
              [&_pre_code]:bg-transparent [&_pre_code]:p-0
              [&_table]:w-full [&_table]:text-sm [&_table]:mb-3
              [&_thead]:border-b [&_thead]:border-(--color-border)
              [&_th]:text-left [&_th]:py-1.5 [&_th]:px-2 [&_th]:text-xs [&_th]:font-medium [&_th]:text-(--color-text-secondary) [&_th]:uppercase
              [&_td]:py-1.5 [&_td]:px-2 [&_td]:text-(--color-text-secondary) [&_td]:border-b [&_td]:border-(--color-border)/30
              [&_a]:text-(--color-accent) [&_a]:underline [&_a]:underline-offset-2
              [&_blockquote]:border-l-2 [&_blockquote]:border-(--color-accent) [&_blockquote]:pl-3 [&_blockquote]:italic [&_blockquote]:text-(--color-text-secondary)
            ">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {data.content}
              </ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </>
  );
}

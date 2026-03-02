import { useQuery } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Loader2 } from "lucide-react";
import { api } from "@/lib/api";

export function GuidePage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["guide"],
    queryFn: () => api.get<{ content: string }>("/guide"),
    staleTime: 5 * 60 * 1000,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-6 h-6 animate-spin text-(--color-accent)" />
      </div>
    );
  }

  if (error || !data?.content) {
    return (
      <div className="p-6">
        <p className="text-sm text-(--color-negative)">Failed to load user guide.</p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="prose prose-invert prose-sm max-w-none
        [&_h1]:text-2xl [&_h1]:font-bold [&_h1]:text-(--color-text-primary) [&_h1]:mb-4 [&_h1]:mt-8 [&_h1]:first:mt-0
        [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-(--color-text-primary) [&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:pt-4 [&_h2]:border-t [&_h2]:border-(--color-border)
        [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-(--color-text-primary) [&_h3]:mb-2 [&_h3]:mt-6
        [&_h4]:text-sm [&_h4]:font-semibold [&_h4]:text-(--color-text-primary) [&_h4]:mb-2 [&_h4]:mt-4
        [&_p]:text-sm [&_p]:text-(--color-text-secondary) [&_p]:leading-relaxed [&_p]:mb-3
        [&_ul]:text-sm [&_ul]:text-(--color-text-secondary) [&_ul]:mb-3 [&_ul]:pl-5 [&_ul]:list-disc
        [&_ol]:text-sm [&_ol]:text-(--color-text-secondary) [&_ol]:mb-3 [&_ol]:pl-5 [&_ol]:list-decimal
        [&_li]:mb-1 [&_li]:leading-relaxed
        [&_strong]:text-(--color-text-primary) [&_strong]:font-semibold
        [&_code]:text-xs [&_code]:bg-(--color-bg-elevated) [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:font-mono [&_code]:text-(--color-accent)
        [&_pre]:bg-(--color-bg-elevated) [&_pre]:rounded-lg [&_pre]:p-4 [&_pre]:mb-4 [&_pre]:overflow-x-auto
        [&_pre_code]:bg-transparent [&_pre_code]:p-0
        [&_table]:w-full [&_table]:text-sm [&_table]:mb-4
        [&_thead]:border-b [&_thead]:border-(--color-border)
        [&_th]:text-left [&_th]:py-2 [&_th]:px-3 [&_th]:text-xs [&_th]:font-medium [&_th]:text-(--color-text-secondary) [&_th]:uppercase [&_th]:tracking-wider
        [&_td]:py-2 [&_td]:px-3 [&_td]:text-(--color-text-secondary) [&_td]:border-b [&_td]:border-(--color-border)/30
        [&_a]:text-(--color-accent) [&_a]:underline [&_a]:underline-offset-2
        [&_blockquote]:border-l-2 [&_blockquote]:border-(--color-accent) [&_blockquote]:pl-4 [&_blockquote]:italic [&_blockquote]:text-(--color-text-secondary)
        [&_hr]:border-(--color-border) [&_hr]:my-6
      ">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {data.content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

import { t } from '@/shared/config/i18n';
import { Badge, type BadgeTone } from '@/shared/ui/badge';

// A GTIN suggestion in the queue means a collision (auto-links never enter curation), so it
// warrants a warning tone; RAG suggestions are informational.
const METHOD_TONE: Record<string, BadgeTone> = {
  gtin_auto: 'warning',
  rag_suggested: 'info',
  manual: 'neutral',
};

export function MethodBadge({ method }: { method: string }) {
  return <Badge tone={METHOD_TONE[method] ?? 'neutral'}>{t.method[method] ?? method}</Badge>;
}

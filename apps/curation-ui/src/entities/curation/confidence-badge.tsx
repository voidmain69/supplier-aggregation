import { confidenceBand } from '@/shared/lib/format';
import { Badge, type BadgeTone } from '@/shared/ui/badge';

const BAND_TONE: Record<string, BadgeTone> = {
  high: 'success',
  medium: 'warning',
  low: 'danger',
};

/** Confidence score with the shared banding colors (curation-ui-plan §9.1). */
export function ConfidenceBadge({ confidence }: { confidence: number }) {
  const band = confidenceBand(confidence);
  return (
    <Badge tone={BAND_TONE[band]} title={`confidence ${confidence.toFixed(3)}`}>
      {(confidence * 100).toFixed(0)}%
    </Badge>
  );
}

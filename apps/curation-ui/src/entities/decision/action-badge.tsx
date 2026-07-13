import { t } from '@/shared/config/i18n';
import { Badge, type BadgeTone } from '@/shared/ui/badge';

const ACTION_TONE: Record<string, BadgeTone> = {
  confirm: 'success',
  reject: 'danger',
  create_new: 'info',
  merge: 'warning',
};

/** A coloured badge for a curation decision action (confirm / reject / create_new / merge). */
export function ActionBadge({ action }: { action: string }) {
  return (
    <Badge tone={ACTION_TONE[action] ?? 'neutral'}>{t.decisions.actions[action] ?? action}</Badge>
  );
}

import { useState } from 'react';

import { t } from '@/shared/config/i18n';
import { Button } from '@/shared/ui/button';
import { Dialog } from '@/shared/ui/dialog';
import { TextInput } from '@/shared/ui/text-input';

import { useMerge } from './use-merge';

/**
 * Merge-into-this-canonical form. The operator pastes the source canonical id (copied from the
 * duplicate's page); the source is removed and its links move here. Irreversible — hence the
 * explicit warning and a distinct danger action.
 */
export function MergeDialog({
  open,
  targetCanonicalId,
  onClose,
}: {
  open: boolean;
  targetCanonicalId: string;
  onClose: () => void;
}) {
  const merge = useMerge(targetCanonicalId);
  const [source, setSource] = useState('');

  const valid = source.trim().length >= 10 && source.trim() !== targetCanonicalId;

  function submit(): void {
    if (!valid || merge.isPending) return;
    merge.mutate(source.trim(), {
      onSuccess: () => {
        setSource('');
        onClose();
      },
    });
  }

  return (
    <Dialog open={open} title={t.canonical.mergeTitle} onClose={onClose}>
      <p className="mb-3 text-sm text-warning">{t.canonical.mergeHint}</p>
      <div className="flex flex-col gap-3">
        <TextInput
          label={t.canonical.mergeSourceLabel}
          value={source}
          className="font-mono"
          onChange={(e) => {
            setSource(e.target.value.trim());
          }}
        />
        {source && !valid ? (
          <p className="text-sm text-danger">{t.canonical.mergeInvalidId}</p>
        ) : null}
        <div className="mt-1 flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose}>
            {t.common.cancel}
          </Button>
          <Button variant="danger" disabled={!valid || merge.isPending} onClick={submit}>
            {t.canonical.merge}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

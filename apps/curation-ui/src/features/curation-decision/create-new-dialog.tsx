import { useState } from 'react';

import { ApiError } from '@/shared/api/http';
import type { SupplierProduct } from '@/shared/api/types';
import { t } from '@/shared/config/i18n';
import { Button } from '@/shared/ui/button';
import { Dialog } from '@/shared/ui/dialog';
import { TextInput } from '@/shared/ui/text-input';

import { useCreateNew } from './use-decision';

/**
 * Create-new-canonical form for the review workspace. Prefilled from the supplier product (the
 * operator can edit), it resolves the queue item on success and hands control back to move on.
 */
export function CreateNewDialog({
  open,
  supplierProductId,
  product,
  onClose,
  onCreated,
}: {
  open: boolean;
  supplierProductId: string;
  product: SupplierProduct | undefined;
  onClose: () => void;
  onCreated: () => void;
}) {
  const createNew = useCreateNew();
  const [title, setTitle] = useState('');
  const [brand, setBrand] = useState('');
  const [gtin, setGtin] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  // Prefill once from the product when the dialog opens.
  if (open && !ready && product) {
    setTitle(product.name);
    setBrand(product.brand ?? '');
    setGtin(product.gtin ?? '');
    setReady(true);
  }

  function close(): void {
    setReady(false);
    setError(null);
    onClose();
  }

  async function submit(): Promise<void> {
    if (!title.trim() || busy) return;
    setBusy(true);
    setError(null);
    try {
      await createNew(supplierProductId, {
        title: title.trim(),
        brand: brand.trim() || null,
        gtin: gtin.trim() || null,
      });
      setReady(false);
      onCreated();
    } catch (err) {
      setError(
        err instanceof ApiError ? (err.problem?.detail ?? err.message) : t.common.errorTitle,
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Dialog open={open} title={t.review.createNewTitle} onClose={close}>
      <p className="mb-3 text-sm text-muted">{t.review.createNewHint}</p>
      <div className="flex flex-col gap-3">
        <TextInput
          label={t.common.title}
          value={title}
          onChange={(e) => {
            setTitle(e.target.value);
          }}
        />
        <TextInput
          label={t.common.brand}
          value={brand}
          onChange={(e) => {
            setBrand(e.target.value);
          }}
        />
        <TextInput
          label={t.common.gtin}
          value={gtin}
          inputMode="numeric"
          onChange={(e) => {
            setGtin(e.target.value.replace(/\D/g, ''));
          }}
        />
        {error ? <p className="text-sm text-danger">{error}</p> : null}
        <div className="mt-1 flex justify-end gap-2">
          <Button variant="ghost" onClick={close}>
            {t.common.cancel}
          </Button>
          <Button variant="success" disabled={busy || !title.trim()} onClick={() => void submit()}>
            {t.review.createNew}
          </Button>
        </div>
      </div>
    </Dialog>
  );
}

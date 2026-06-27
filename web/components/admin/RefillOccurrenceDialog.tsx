"use client";

import { useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { AdminRefillOccurrence } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Modal } from "@/components/ui/Modal";
import { Button, Badge } from "@/components/ui/primitives";
import { Field, Input } from "@/components/ui/form";

export function RefillOccurrenceDialog({
  occurrence,
  onClose,
  onChanged,
}: {
  occurrence: AdminRefillOccurrence;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [refillOn, setRefillOn] = useState(occurrence.refillOn);
  const [quantity, setQuantity] = useState(occurrence.quantity);
  const [busy, setBusy] = useState<null | "save" | "cancel" | "revert">(null);
  const [error, setError] = useState<string | null>(null);

  const base = `/api/prescriptions/${occurrence.prescriptionId}/exceptions`;
  const slot = occurrence.occurrenceDate;

  async function run(action: "save" | "cancel" | "revert", fn: () => Promise<unknown>) {
    setBusy(action);
    setError(null);
    try {
      await fn();
      onChanged();
      onClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setBusy(null);
    }
  }

  const save = () =>
    run("save", () =>
      api.put(base, { occurrenceDate: slot, refillOn, quantity }),
    );
  const skip = () =>
    run("cancel", () => api.put(base, { occurrenceDate: slot, cancelled: true }));
  const revert = () =>
    run("revert", () => api.del(`${base}?at=${encodeURIComponent(slot)}`));

  return (
    <Modal open onClose={onClose} title="Edit this refill">
      <div className="mb-4 flex items-center gap-2 text-sm text-slate-500">
        <span>
          {occurrence.medication} {occurrence.dosage} · originally {formatDate(occurrence.occurrenceDate)}
        </span>
        {occurrence.cancelled ? (
          <Badge color="red">Skipped</Badge>
        ) : occurrence.overridden ? (
          <Badge color="amber">Adjusted</Badge>
        ) : (
          <Badge color="teal">From series</Badge>
        )}
      </div>

      {occurrence.cancelled ? (
        <p className="text-sm text-slate-600">
          This refill is skipped. You can restore it back to the series schedule.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <Field label="Refill date">
            <Input type="date" value={refillOn} onChange={(e) => setRefillOn(e.target.value)} />
          </Field>
          <Field label="Quantity">
            <Input
              type="number"
              min={1}
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
            />
          </Field>
        </div>
      )}

      {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
        <div>
          {(occurrence.overridden || occurrence.cancelled) && (
            <Button variant="secondary" loading={busy === "revert"} onClick={revert}>
              Revert to series
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          {!occurrence.cancelled && (
            <Button variant="danger" loading={busy === "cancel"} onClick={skip}>
              Skip this refill
            </Button>
          )}
          {!occurrence.cancelled && (
            <Button loading={busy === "save"} onClick={save}>
              Save changes
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

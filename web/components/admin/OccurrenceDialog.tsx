"use client";

import { useState } from "react";
import { format, parseISO } from "date-fns";

import { api, ApiError } from "@/lib/api";
import type { AdminOccurrence } from "@/lib/types";
import { formatDate } from "@/lib/format";
import { Modal } from "@/components/ui/Modal";
import { Button, Badge } from "@/components/ui/primitives";
import { Field, Input } from "@/components/ui/form";

const toLocalInput = (iso: string) => format(parseISO(iso), "yyyy-MM-dd'T'HH:mm");

/**
 * Edit a single occurrence of a recurring appointment: reschedule it, cancel
 * just that occurrence, or revert it back to the series. Edits are stored as
 * exceptions keyed by the occurrence's original slot.
 */
export function OccurrenceDialog({
  occurrence,
  onClose,
  onChanged,
}: {
  occurrence: AdminOccurrence;
  onClose: () => void;
  onChanged: () => void;
}) {
  const [provider, setProvider] = useState(occurrence.provider);
  const [startAt, setStartAt] = useState(toLocalInput(occurrence.occursAt));
  const [busy, setBusy] = useState<null | "save" | "cancel" | "revert">(null);
  const [error, setError] = useState<string | null>(null);

  const base = `/api/appointments/${occurrence.appointmentId}/exceptions`;
  const slot = occurrence.occurrenceStart;

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

  const reschedule = () =>
    run("save", () =>
      api.put(base, {
        occurrenceStart: slot,
        provider,
        startAt: new Date(startAt).toISOString(),
      }),
    );
  const cancel = () =>
    run("cancel", () => api.put(base, { occurrenceStart: slot, cancelled: true }));
  const revert = () =>
    run("revert", () => api.del(`${base}?at=${encodeURIComponent(slot)}`));

  return (
    <Modal open onClose={onClose} title="Edit this occurrence">
      <div className="mb-4 flex items-center gap-2 text-sm text-slate-500">
        <span>Originally {formatDate(occurrence.occurrenceStart.slice(0, 10))}</span>
        {occurrence.cancelled ? (
          <Badge color="red">Cancelled</Badge>
        ) : occurrence.overridden ? (
          <Badge color="amber">Rescheduled</Badge>
        ) : (
          <Badge color="teal">From series</Badge>
        )}
      </div>

      {occurrence.cancelled ? (
        <p className="text-sm text-slate-600">
          This occurrence is cancelled. You can restore it back to the series schedule.
        </p>
      ) : (
        <div className="space-y-4">
          <Field label="Provider">
            <Input value={provider} onChange={(e) => setProvider(e.target.value)} />
          </Field>
          <Field label="Date & time">
            <Input
              type="datetime-local"
              value={startAt}
              onChange={(e) => setStartAt(e.target.value)}
            />
          </Field>
        </div>
      )}

      {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="mt-5 flex flex-wrap items-center justify-between gap-2">
        {/* Revert is available whenever this occurrence diverges from the series. */}
        <div>
          {(occurrence.overridden || occurrence.cancelled) && (
            <Button variant="secondary" loading={busy === "revert"} onClick={revert}>
              Revert to series
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          {!occurrence.cancelled && (
            <Button variant="danger" loading={busy === "cancel"} onClick={cancel}>
              Cancel this occurrence
            </Button>
          )}
          {!occurrence.cancelled && (
            <Button loading={busy === "save"} onClick={reschedule}>
              Save changes
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

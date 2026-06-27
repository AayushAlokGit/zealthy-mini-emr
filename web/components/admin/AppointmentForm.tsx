"use client";

import { useState } from "react";
import { format, parseISO } from "date-fns";

import { ApiError } from "@/lib/api";
import type { Appointment, Repeat } from "@/lib/types";
import { Button } from "@/components/ui/primitives";
import { Field, Input, Select } from "@/components/ui/form";

export interface AppointmentPayload {
  provider: string;
  startAt: string;
  repeat: Repeat;
  until: string | null;
}

interface Props {
  existing?: Appointment;
  onSubmit: (payload: AppointmentPayload) => Promise<void>;
  onDone: () => void;
}

const toLocalInput = (iso: string) => format(parseISO(iso), "yyyy-MM-dd'T'HH:mm");

export function AppointmentForm({ existing, onSubmit, onDone }: Props) {
  const [provider, setProvider] = useState(existing?.provider ?? "");
  const [startAt, setStartAt] = useState(existing ? toLocalInput(existing.startAt) : "");
  const [repeat, setRepeat] = useState<Repeat>(existing?.repeat ?? "NONE");
  const [until, setUntil] = useState(existing?.until ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        provider,
        startAt: new Date(startAt).toISOString(),
        repeat,
        until: repeat !== "NONE" && until ? until : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Provider">
        <Input required placeholder="Dr Jane Smith" value={provider} onChange={(e) => setProvider(e.target.value)} />
      </Field>
      <Field label="First appointment">
        <Input type="datetime-local" required value={startAt} onChange={(e) => setStartAt(e.target.value)} />
      </Field>
      <Field label="Repeats">
        <Select value={repeat} onChange={(e) => setRepeat(e.target.value as Repeat)}>
          <option value="NONE">Does not repeat</option>
          <option value="WEEKLY">Weekly</option>
          <option value="MONTHLY">Monthly</option>
        </Select>
      </Field>
      {repeat !== "NONE" && (
        <Field label="End recurrence on" hint="Optional — leave blank for ongoing.">
          <Input type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
        </Field>
      )}

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" loading={submitting}>
          {existing ? "Save changes" : "Schedule"}
        </Button>
      </div>
    </form>
  );
}

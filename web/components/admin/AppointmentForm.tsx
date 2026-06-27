"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { format, parseISO } from "date-fns";

import { ApiError } from "@/lib/api";
import { appointmentSchema, type AppointmentForm as Values } from "@/lib/schemas";
import type { Appointment } from "@/lib/types";
import { Button } from "@/components/ui/primitives";
import { Field, Input, Select } from "@/components/ui/form";

export interface AppointmentPayload {
  provider: string;
  startAt: string; // UTC ISO
  repeat: Values["repeat"];
  until: string | null;
}

interface Props {
  existing?: Appointment;
  onSubmit: (payload: AppointmentPayload) => Promise<void>;
  onDone: () => void;
}

const toLocalInput = (iso: string) => format(parseISO(iso), "yyyy-MM-dd'T'HH:mm");

export function AppointmentForm({ existing, onSubmit, onDone }: Props) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(appointmentSchema),
    defaultValues: existing
      ? {
          provider: existing.provider,
          startAt: toLocalInput(existing.startAt),
          repeat: existing.repeat,
          until: existing.until ?? "",
        }
      : { repeat: "NONE", provider: "", startAt: "", until: "" },
  });

  const repeat = watch("repeat");

  async function submit(values: Values) {
    setServerError(null);
    try {
      await onSubmit({
        provider: values.provider,
        // datetime-local is local wall-clock → convert to UTC ISO for the API.
        startAt: new Date(values.startAt).toISOString(),
        repeat: values.repeat,
        until: values.repeat !== "NONE" && values.until ? values.until : null,
      });
      onDone();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong.");
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      <Field label="Provider" error={errors.provider?.message}>
        <Input placeholder="Dr Jane Smith" {...register("provider")} />
      </Field>
      <Field label="First appointment" error={errors.startAt?.message}>
        <Input type="datetime-local" {...register("startAt")} />
      </Field>
      <Field label="Repeats" error={errors.repeat?.message}>
        <Select {...register("repeat")}>
          <option value="NONE">Does not repeat</option>
          <option value="WEEKLY">Weekly</option>
          <option value="MONTHLY">Monthly</option>
        </Select>
      </Field>
      {repeat !== "NONE" && (
        <Field label="End recurrence on" error={errors.until?.message} hint="Optional — leave blank for ongoing.">
          <Input type="date" {...register("until")} />
        </Field>
      )}

      {serverError && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{serverError}</p>
      )}

      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="secondary" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" loading={isSubmitting}>
          {existing ? "Save changes" : "Schedule"}
        </Button>
      </div>
    </form>
  );
}

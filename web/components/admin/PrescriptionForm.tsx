"use client";

import { useState } from "react";
import useSWR from "swr";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { ApiError, fetcher } from "@/lib/api";
import { prescriptionSchema, type PrescriptionForm as Values } from "@/lib/schemas";
import type { Prescription } from "@/lib/types";
import { Button } from "@/components/ui/primitives";
import { Field, Input, Select } from "@/components/ui/form";

export interface PrescriptionPayload {
  medication: string;
  dosage: string;
  quantity: number;
  refillOn: string;
  refillSchedule: Values["refillSchedule"];
  until: string | null;
}

interface Props {
  existing?: Prescription;
  onSubmit: (payload: PrescriptionPayload) => Promise<void>;
  onDone: () => void;
}

export function PrescriptionForm({ existing, onSubmit, onDone }: Props) {
  const [serverError, setServerError] = useState<string | null>(null);
  const { data: medications } = useSWR<string[]>("/api/medications", fetcher);
  const { data: dosages } = useSWR<string[]>("/api/dosages", fetcher);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<Values>({
    resolver: zodResolver(prescriptionSchema),
    defaultValues: existing
      ? {
          medication: existing.medication,
          dosage: existing.dosage,
          quantity: existing.quantity,
          refillOn: existing.refillOn,
          refillSchedule: existing.refillSchedule,
          until: existing.until ?? "",
        }
      : { quantity: 1, refillSchedule: "MONTHLY", medication: "", dosage: "", refillOn: "", until: "" },
  });

  const schedule = watch("refillSchedule");

  async function submit(values: Values) {
    setServerError(null);
    try {
      await onSubmit({
        medication: values.medication,
        dosage: values.dosage,
        quantity: values.quantity,
        refillOn: values.refillOn,
        refillSchedule: values.refillSchedule,
        until: values.refillSchedule !== "NONE" && values.until ? values.until : null,
      });
      onDone();
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong.");
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Medication" error={errors.medication?.message}>
          <Select {...register("medication")}>
            <option value="">Select…</option>
            {medications?.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Dosage" error={errors.dosage?.message}>
          <Select {...register("dosage")}>
            <option value="">Select…</option>
            {dosages?.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Quantity" error={errors.quantity?.message}>
          <Input type="number" min={1} {...register("quantity", { valueAsNumber: true })} />
        </Field>
        <Field label="First refill on" error={errors.refillOn?.message}>
          <Input type="date" {...register("refillOn")} />
        </Field>
      </div>
      <Field label="Refill schedule" error={errors.refillSchedule?.message}>
        <Select {...register("refillSchedule")}>
          <option value="NONE">One-time</option>
          <option value="WEEKLY">Weekly</option>
          <option value="MONTHLY">Monthly</option>
        </Select>
      </Field>
      {schedule !== "NONE" && (
        <Field label="End refills on" error={errors.until?.message} hint="Optional — leave blank for ongoing.">
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
          {existing ? "Save changes" : "Prescribe"}
        </Button>
      </div>
    </form>
  );
}

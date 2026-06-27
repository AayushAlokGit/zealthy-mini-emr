"use client";

import { useEffect, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { Prescription, Repeat } from "@/lib/types";
import { Button } from "@/components/ui/primitives";
import { Field, Input, Select } from "@/components/ui/form";

export interface PrescriptionPayload {
  medication: string;
  dosage: string;
  quantity: number;
  refillOn: string;
  refillSchedule: Repeat;
  until: string | null;
}

interface Props {
  existing?: Prescription;
  onSubmit: (payload: PrescriptionPayload) => Promise<void>;
  onDone: () => void;
}

export function PrescriptionForm({ existing, onSubmit, onDone }: Props) {
  const [medications, setMedications] = useState<string[]>([]);
  const [dosages, setDosages] = useState<string[]>([]);

  const [medication, setMedication] = useState(existing?.medication ?? "");
  const [dosage, setDosage] = useState(existing?.dosage ?? "");
  const [quantity, setQuantity] = useState(existing?.quantity ?? 1);
  const [refillOn, setRefillOn] = useState(existing?.refillOn ?? "");
  const [refillSchedule, setRefillSchedule] = useState<Repeat>(existing?.refillSchedule ?? "MONTHLY");
  const [until, setUntil] = useState(existing?.until ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadOptions() {
      try {
        const [meds, doses] = await Promise.all([
          api.get<string[]>("/api/medications"),
          api.get<string[]>("/api/dosages"),
        ]);
        if (!cancelled) {
          setMedications(meds);
          setDosages(doses);
        }
      } catch {
        // dropdowns stay empty if the lookups fail
      }
    }
    loadOptions();
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({
        medication,
        dosage,
        quantity,
        refillOn,
        refillSchedule,
        until: refillSchedule !== "NONE" && until ? until : null,
      });
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <Field label="Medication">
          <Select required value={medication} onChange={(e) => setMedication(e.target.value)}>
            <option value="">Select…</option>
            {medications.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Dosage">
          <Select required value={dosage} onChange={(e) => setDosage(e.target.value)}>
            <option value="">Select…</option>
            {dosages.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Quantity">
          <Input
            type="number"
            min={1}
            required
            value={quantity}
            onChange={(e) => setQuantity(Number(e.target.value))}
          />
        </Field>
        <Field label="First refill on">
          <Input type="date" required value={refillOn} onChange={(e) => setRefillOn(e.target.value)} />
        </Field>
      </div>
      <Field label="Refill schedule">
        <Select value={refillSchedule} onChange={(e) => setRefillSchedule(e.target.value as Repeat)}>
          <option value="NONE">One-time</option>
          <option value="WEEKLY">Weekly</option>
          <option value="MONTHLY">Monthly</option>
        </Select>
      </Field>
      {refillSchedule !== "NONE" && (
        <Field label="End refills on" hint="Optional — leave blank for ongoing.">
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
          {existing ? "Save changes" : "Prescribe"}
        </Button>
      </div>
    </form>
  );
}

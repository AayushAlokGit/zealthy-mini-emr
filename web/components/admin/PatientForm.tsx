"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { ApiError } from "@/lib/api";
import { patientSchema, patientEditSchema, type PatientForm as PatientFormValues } from "@/lib/schemas";
import { Button } from "@/components/ui/primitives";
import { Field, Input } from "@/components/ui/form";

interface Props {
  mode: "create" | "edit";
  defaultValues?: Partial<PatientFormValues>;
  onSubmit: (values: PatientFormValues) => Promise<void>;
  submitLabel: string;
}

export function PatientForm({ mode, defaultValues, onSubmit, submitLabel }: Props) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<PatientFormValues>({
    resolver: zodResolver(mode === "create" ? patientSchema : patientEditSchema),
    defaultValues,
  });

  async function submit(values: PatientFormValues) {
    setServerError(null);
    try {
      await onSubmit(values);
    } catch (err) {
      setServerError(err instanceof ApiError ? err.message : "Something went wrong.");
    }
  }

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4">
      <Field label="Full name" error={errors.name?.message}>
        <Input placeholder="Jane Doe" {...register("name")} />
      </Field>
      <Field label="Email" error={errors.email?.message}>
        <Input type="email" placeholder="jane@example.com" {...register("email")} />
      </Field>
      <Field
        label={mode === "create" ? "Password" : "New password"}
        error={errors.password?.message}
        hint={mode === "edit" ? "Leave blank to keep the current password." : undefined}
      >
        <Input type="text" placeholder="At least 6 characters" {...register("password")} />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Date of birth" error={errors.dob?.message}>
          <Input type="date" {...register("dob")} />
        </Field>
        <Field label="Phone" error={errors.phone?.message}>
          <Input placeholder="555-123-4567" {...register("phone")} />
        </Field>
      </div>

      {serverError && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{serverError}</p>
      )}

      <Button type="submit" loading={isSubmitting}>
        {submitLabel}
      </Button>
    </form>
  );
}

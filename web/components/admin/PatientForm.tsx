"use client";

import { useState } from "react";

import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/primitives";
import { Field, Input } from "@/components/ui/form";

export interface PatientFormValues {
  name: string;
  email: string;
  password: string;
  dob?: string;
  phone?: string;
}

interface Props {
  mode: "create" | "edit";
  defaultValues?: Partial<PatientFormValues>;
  onSubmit: (values: PatientFormValues) => Promise<void>;
  submitLabel: string;
}

export function PatientForm({ mode, defaultValues, onSubmit, submitLabel }: Props) {
  const [name, setName] = useState(defaultValues?.name ?? "");
  const [email, setEmail] = useState(defaultValues?.email ?? "");
  const [password, setPassword] = useState("");
  const [dob, setDob] = useState(defaultValues?.dob ?? "");
  const [phone, setPhone] = useState(defaultValues?.phone ?? "");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit({ name, email, password, dob, phone });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <Field label="Full name">
        <Input required placeholder="Jane Doe" value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Field label="Email">
        <Input
          type="email"
          required
          placeholder="jane@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </Field>
      <Field
        label={mode === "create" ? "Password" : "New password"}
        hint={mode === "edit" ? "Leave blank to keep the current password." : undefined}
      >
        <Input
          type="text"
          required={mode === "create"}
          minLength={6}
          placeholder="At least 6 characters"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </Field>
      <div className="grid grid-cols-2 gap-4">
        <Field label="Date of birth">
          <Input type="date" value={dob} onChange={(e) => setDob(e.target.value)} />
        </Field>
        <Field label="Phone">
          <Input placeholder="555-123-4567" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </Field>
      </div>

      {error && (
        <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{error}</p>
      )}

      <Button type="submit" loading={submitting}>
        {submitLabel}
      </Button>
    </form>
  );
}

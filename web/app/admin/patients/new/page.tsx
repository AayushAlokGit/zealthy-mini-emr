"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft } from "lucide-react";

import { api } from "@/lib/api";
import type { Patient } from "@/lib/types";
import type { PatientForm as PatientFormValues } from "@/lib/schemas";
import { AdminHeader } from "@/components/admin/AdminHeader";
import { PatientForm } from "@/components/admin/PatientForm";
import { Card } from "@/components/ui/primitives";

export default function NewPatientPage() {
  const router = useRouter();

  async function handleCreate(values: PatientFormValues) {
    const patient = await api.post<Patient>("/api/patients", {
      ...values,
      dob: values.dob || null,
      phone: values.phone || null,
    });
    router.push(`/admin/patients/${patient.id}`);
  }

  return (
    <div className="min-h-screen">
      <AdminHeader />
      <main className="mx-auto max-w-xl px-4 py-6">
        <Link
          href="/admin"
          className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
        >
          <ArrowLeft className="h-4 w-4" /> Back to patients
        </Link>
        <h1 className="mb-1 text-2xl font-semibold text-slate-800">New patient</h1>
        <p className="mb-5 text-sm text-slate-500">
          Create a patient record. They can immediately log in to the portal with this password.
        </p>
        <Card className="p-6">
          <PatientForm mode="create" onSubmit={handleCreate} submitLabel="Create patient" />
        </Card>
      </main>
    </div>
  );
}

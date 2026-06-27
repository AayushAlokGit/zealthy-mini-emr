"use client";

import { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import useSWR from "swr";
import { parseISO, format } from "date-fns";
import { ArrowLeft, Pencil, Plus, Trash2, CalendarOff, CalendarDays } from "lucide-react";

import { api, fetcher } from "@/lib/api";
import type {
  Patient,
  Appointment,
  Prescription,
  AdminOccurrence,
  AdminRefillOccurrence,
} from "@/lib/types";
import type { PatientForm as PatientValues } from "@/lib/schemas";
import { formatDate, formatDateTime, formatTime, repeatLabel } from "@/lib/format";
import { AdminHeader } from "@/components/admin/AdminHeader";
import { PatientForm } from "@/components/admin/PatientForm";
import { AppointmentForm, type AppointmentPayload } from "@/components/admin/AppointmentForm";
import { PrescriptionForm, type PrescriptionPayload } from "@/components/admin/PrescriptionForm";
import { OccurrenceDialog } from "@/components/admin/OccurrenceDialog";
import { RefillOccurrenceDialog } from "@/components/admin/RefillOccurrenceDialog";
import { Calendar, type CalendarEvent } from "@/components/Calendar";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { Modal } from "@/components/ui/Modal";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/feedback";

export default function PatientDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const patient = useSWR<Patient>(`/api/patients/${id}`, fetcher);
  const appts = useSWR<Appointment[]>(`/api/patients/${id}/appointments`, fetcher);
  const rxs = useSWR<Prescription[]>(`/api/patients/${id}/prescriptions`, fetcher);

  const [editingPatient, setEditingPatient] = useState(false);

  async function updatePatient(values: PatientValues) {
    await api.patch(`/api/patients/${id}`, {
      name: values.name,
      email: values.email,
      dob: values.dob || null,
      phone: values.phone || null,
      ...(values.password ? { password: values.password } : {}),
    });
    setEditingPatient(false);
    patient.mutate();
  }

  if (patient.isLoading) {
    return (
      <Shell>
        <LoadingState />
      </Shell>
    );
  }
  if (patient.error || !patient.data) {
    return (
      <Shell>
        <ErrorState message="Patient not found." />
      </Shell>
    );
  }

  const p = patient.data;

  return (
    <Shell>
      <Link
        href="/admin"
        className="mb-4 inline-flex items-center gap-1 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="h-4 w-4" /> Back to patients
      </Link>

      <Card className="mb-6 p-5">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">{p.name}</h1>
            <p className="text-sm text-slate-500">{p.email}</p>
            <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-600">
              <span>Phone: {p.phone ?? "—"}</span>
              <span>DOB: {p.dob ? formatDate(p.dob) : "—"}</span>
            </div>
          </div>
          <Button variant="secondary" onClick={() => setEditingPatient(true)}>
            <Pencil className="h-4 w-4" /> Edit
          </Button>
        </div>
      </Card>

      <AppointmentsSection patientId={id} swr={appts} />
      <PrescriptionsSection patientId={id} swr={rxs} />

      <Modal open={editingPatient} onClose={() => setEditingPatient(false)} title="Edit patient">
        <PatientForm
          mode="edit"
          defaultValues={{
            name: p.name,
            email: p.email,
            password: "",
            dob: p.dob ?? "",
            phone: p.phone ?? "",
          }}
          onSubmit={updatePatient}
          submitLabel="Save changes"
        />
      </Modal>
    </Shell>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen">
      <AdminHeader />
      <main className="mx-auto max-w-4xl px-4 py-6">{children}</main>
    </div>
  );
}

function AppointmentsSection({
  patientId,
  swr,
}: {
  patientId: string;
  swr: ReturnType<typeof useSWR<Appointment[]>>;
}) {
  const { data, isLoading, error, mutate } = swr;
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Appointment | null>(null);
  const [deleting, setDeleting] = useState<Appointment | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);
  const [editingOcc, setEditingOcc] = useState<AdminOccurrence | null>(null);

  const schedule = useSWR<AdminOccurrence[]>(
    showCalendar ? `/api/patients/${patientId}/schedule` : null,
    fetcher,
  );

  function refreshAll() {
    mutate();
    schedule.mutate();
  }

  async function create(payload: AppointmentPayload) {
    await api.post(`/api/patients/${patientId}/appointments`, payload);
    refreshAll();
  }
  async function update(payload: AppointmentPayload) {
    if (!editing) return;
    await api.patch(`/api/appointments/${editing.id}`, payload);
    refreshAll();
  }
  async function endSeries(appt: Appointment) {
    await api.patch(`/api/appointments/${appt.id}`, { until: format(new Date(), "yyyy-MM-dd") });
    refreshAll();
  }
  async function remove() {
    if (!deleting) return;
    await api.del(`/api/appointments/${deleting.id}`);
    setDeleting(null);
    refreshAll();
  }

  const events: CalendarEvent[] =
    schedule.data?.map((o) => ({
      date: parseISO(o.occursAt),
      title: o.provider,
      subtitle: `${formatTime(o.occursAt)}${o.cancelled ? " · cancelled" : o.overridden ? " · rescheduled" : ""}`,
      color: "teal",
      cancelled: o.cancelled,
      payload: o,
    })) ?? [];

  return (
    <Card className="mb-6">
      <SectionBar
        title="Appointments"
        count={data?.length ?? 0}
        onAdd={() => setShowForm(true)}
        addLabel="Add appointment"
        rightSlot={
          data && data.length > 0 ? (
            <Button variant="ghost" onClick={() => setShowCalendar((v) => !v)}>
              <CalendarDays className="h-4 w-4" /> {showCalendar ? "List" : "Calendar"}
            </Button>
          ) : null
        }
      />
      <div className="p-4">
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message="Could not load appointments." onRetry={() => mutate()} />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No appointments" hint="Schedule the first one." />
        ) : showCalendar ? (
          schedule.isLoading ? (
            <LoadingState />
          ) : (
            <Calendar events={events} onSelectEvent={(e) => setEditingOcc(e.payload as AdminOccurrence)} />
          )
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.map((a) => (
              <li key={a.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{a.provider}</p>
                  <p className="text-xs text-slate-500">
                    {formatDateTime(a.startAt)} · {repeatLabel(a.repeat)}
                    {a.until && ` · ends ${formatDate(a.until)}`}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  {a.repeat !== "NONE" && !a.until && (
                    <Button variant="ghost" onClick={() => endSeries(a)} title="End recurrence">
                      <CalendarOff className="h-4 w-4" /> End series
                    </Button>
                  )}
                  <IconBtn label="Edit" onClick={() => setEditing(a)}>
                    <Pencil className="h-4 w-4" />
                  </IconBtn>
                  <IconBtn label="Delete" danger onClick={() => setDeleting(a)}>
                    <Trash2 className="h-4 w-4" />
                  </IconBtn>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {editingOcc && (
        <OccurrenceDialog
          occurrence={editingOcc}
          onClose={() => setEditingOcc(null)}
          onChanged={refreshAll}
        />
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title="New appointment">
        <AppointmentForm onSubmit={create} onDone={() => setShowForm(false)} />
      </Modal>
      <Modal open={!!editing} onClose={() => setEditing(null)} title="Edit appointment">
        {editing && (
          <AppointmentForm existing={editing} onSubmit={update} onDone={() => setEditing(null)} />
        )}
      </Modal>
      <ConfirmModal
        open={!!deleting}
        title="Cancel appointment?"
        message={`This will remove the appointment with ${deleting?.provider}. The patient will be notified.`}
        onCancel={() => setDeleting(null)}
        onConfirm={remove}
      />
    </Card>
  );
}

function PrescriptionsSection({
  patientId,
  swr,
}: {
  patientId: string;
  swr: ReturnType<typeof useSWR<Prescription[]>>;
}) {
  const { data, isLoading, error, mutate } = swr;
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Prescription | null>(null);
  const [deleting, setDeleting] = useState<Prescription | null>(null);
  const [showCalendar, setShowCalendar] = useState(false);
  const [editingOcc, setEditingOcc] = useState<AdminRefillOccurrence | null>(null);

  const schedule = useSWR<AdminRefillOccurrence[]>(
    showCalendar ? `/api/patients/${patientId}/refill-schedule` : null,
    fetcher,
  );

  function refreshAll() {
    mutate();
    schedule.mutate();
  }

  async function create(payload: PrescriptionPayload) {
    await api.post(`/api/patients/${patientId}/prescriptions`, payload);
    refreshAll();
  }
  async function update(payload: PrescriptionPayload) {
    if (!editing) return;
    await api.patch(`/api/prescriptions/${editing.id}`, payload);
    refreshAll();
  }
  async function remove() {
    if (!deleting) return;
    await api.del(`/api/prescriptions/${deleting.id}`);
    setDeleting(null);
    refreshAll();
  }

  const events: CalendarEvent[] =
    schedule.data?.map((o) => ({
      date: parseISO(`${o.refillOn}T00:00:00`),
      title: `${o.medication} ${o.dosage}`,
      subtitle: `Qty ${o.quantity}${o.cancelled ? " · skipped" : o.overridden ? " · adjusted" : ""}`,
      color: "amber",
      cancelled: o.cancelled,
      payload: o,
    })) ?? [];

  return (
    <Card className="mb-6">
      <SectionBar
        title="Prescriptions"
        count={data?.length ?? 0}
        onAdd={() => setShowForm(true)}
        addLabel="Add prescription"
        rightSlot={
          data && data.length > 0 ? (
            <Button variant="ghost" onClick={() => setShowCalendar((v) => !v)}>
              <CalendarDays className="h-4 w-4" /> {showCalendar ? "List" : "Refill calendar"}
            </Button>
          ) : null
        }
      />
      <div className="p-4">
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message="Could not load prescriptions." onRetry={() => mutate()} />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No prescriptions" hint="Prescribe the first medication." />
        ) : showCalendar ? (
          schedule.isLoading ? (
            <LoadingState />
          ) : (
            <Calendar events={events} onSelectEvent={(e) => setEditingOcc(e.payload as AdminRefillOccurrence)} />
          )
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.map((r) => (
              <li key={r.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {r.medication} <Badge>{r.dosage}</Badge>
                  </p>
                  <p className="text-xs text-slate-500">
                    Qty {r.quantity} · {repeatLabel(r.refillSchedule)} · next {formatDate(r.refillOn)}
                    {r.until && ` · ends ${formatDate(r.until)}`}
                  </p>
                </div>
                <div className="flex items-center gap-1">
                  <IconBtn label="Edit" onClick={() => setEditing(r)}>
                    <Pencil className="h-4 w-4" />
                  </IconBtn>
                  <IconBtn label="Delete" danger onClick={() => setDeleting(r)}>
                    <Trash2 className="h-4 w-4" />
                  </IconBtn>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {editingOcc && (
        <RefillOccurrenceDialog
          occurrence={editingOcc}
          onClose={() => setEditingOcc(null)}
          onChanged={refreshAll}
        />
      )}

      <Modal open={showForm} onClose={() => setShowForm(false)} title="New prescription">
        <PrescriptionForm onSubmit={create} onDone={() => setShowForm(false)} />
      </Modal>
      <Modal open={!!editing} onClose={() => setEditing(null)} title="Edit prescription">
        {editing && (
          <PrescriptionForm existing={editing} onSubmit={update} onDone={() => setEditing(null)} />
        )}
      </Modal>
      <ConfirmModal
        open={!!deleting}
        title="Discontinue prescription?"
        message={`This will remove ${deleting?.medication} ${deleting?.dosage}. The patient will be notified.`}
        onCancel={() => setDeleting(null)}
        onConfirm={remove}
      />
    </Card>
  );
}

function SectionBar({
  title,
  count,
  onAdd,
  addLabel,
  rightSlot,
}: {
  title: string;
  count: number;
  onAdd: () => void;
  addLabel: string;
  rightSlot?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between border-b border-slate-100 px-5 py-3">
      <div className="flex items-center gap-2">
        <h2 className="font-semibold text-slate-800">{title}</h2>
        <Badge>{count}</Badge>
      </div>
      <div className="flex items-center gap-1">
        {rightSlot}
        <Button onClick={onAdd}>
          <Plus className="h-4 w-4" /> {addLabel}
        </Button>
      </div>
    </div>
  );
}

function IconBtn({
  children,
  onClick,
  label,
  danger,
  title,
}: {
  children: React.ReactNode;
  onClick: () => void;
  label: string;
  danger?: boolean;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      title={title ?? label}
      className={`rounded-md p-2 transition-colors ${
        danger ? "text-slate-400 hover:bg-red-50 hover:text-red-600" : "text-slate-400 hover:bg-slate-100 hover:text-slate-700"
      }`}
    >
      {children}
    </button>
  );
}

function ConfirmModal({
  open,
  title,
  message,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => Promise<void> | void;
  onCancel: () => void;
}) {
  const [busy, setBusy] = useState(false);
  async function confirm() {
    setBusy(true);
    try {
      await onConfirm();
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal open={open} onClose={onCancel} title={title}>
      <p className="text-sm text-slate-600">{message}</p>
      <div className="mt-5 flex justify-end gap-2">
        <Button variant="secondary" onClick={onCancel}>
          Keep
        </Button>
        <Button variant="danger" loading={busy} onClick={confirm}>
          Confirm
        </Button>
      </div>
    </Modal>
  );
}

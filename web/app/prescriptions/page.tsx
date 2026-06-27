"use client";

import { useEffect, useState } from "react";
import { parseISO } from "date-fns";
import { CalendarDays, List, Pill } from "lucide-react";

import { api } from "@/lib/api";
import type { Prescription, RefillOccurrence } from "@/lib/types";
import { formatDate, repeatLabel } from "@/lib/format";
import { PortalShell } from "@/components/portal/PortalShell";
import { Calendar, type CalendarEvent } from "@/components/Calendar";
import { Card, Badge } from "@/components/ui/primitives";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/feedback";
import { cn } from "@/components/ui/cn";

export default function PrescriptionsPage() {
  return (
    <PortalShell>
      <Prescriptions />
    </PortalShell>
  );
}

function Prescriptions() {
  const [view, setView] = useState<"list" | "calendar">("list");
  const [reloadKey, setReloadKey] = useState(0);

  const [rx, setRx] = useState<Prescription[] | null>(null);
  const [rxLoading, setRxLoading] = useState(true);
  const [rxError, setRxError] = useState(false);

  const [refills, setRefills] = useState<RefillOccurrence[] | null>(null);
  const [refillsLoading, setRefillsLoading] = useState(true);
  const [refillsError, setRefillsError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadRx() {
      try {
        const list = await api.get<Prescription[]>("/api/me/prescriptions");
        if (!cancelled) {
          setRx(list);
          setRxError(false);
        }
      } catch {
        if (!cancelled) setRxError(true);
      } finally {
        if (!cancelled) setRxLoading(false);
      }
    }

    async function loadRefills() {
      try {
        const list = await api.get<RefillOccurrence[]>("/api/me/refills");
        if (!cancelled) {
          setRefills(list);
          setRefillsError(false);
        }
      } catch {
        if (!cancelled) setRefillsError(true);
      } finally {
        if (!cancelled) setRefillsLoading(false);
      }
    }

    loadRx();
    loadRefills();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const reload = () => setReloadKey((k) => k + 1);

  const events: CalendarEvent[] =
    refills?.map((r) => ({
      date: parseISO(`${r.refillOn}T00:00:00`),
      title: r.medication,
      subtitle: `${r.dosage} · Qty ${r.quantity}`,
      color: "amber",
    })) ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Prescriptions</h1>
        <p className="mt-1 text-sm text-slate-500">All of your medications and refill schedule.</p>
      </div>

      <Card className="p-5">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
          Your medications
        </h2>
        {rxLoading ? (
          <LoadingState />
        ) : rxError ? (
          <ErrorState message="Could not load prescriptions." onRetry={reload} />
        ) : !rx || rx.length === 0 ? (
          <EmptyState title="No prescriptions on file" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {rx.map((p) => (
              <div key={p.id} className="rounded-lg border border-slate-200 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Pill className="h-4 w-4 text-teal-600" />
                    <span className="font-medium text-slate-800">{p.medication}</span>
                  </div>
                  <Badge>{p.dosage}</Badge>
                </div>
                <dl className="mt-3 grid grid-cols-2 gap-2 text-xs">
                  <Detail label="Quantity" value={String(p.quantity)} />
                  <Detail label="Schedule" value={repeatLabel(p.refillSchedule)} />
                  <Detail label="Next refill" value={formatDate(p.refillOn)} />
                  <Detail label="Ends" value={p.until ? formatDate(p.until) : "Ongoing"} />
                </dl>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card className="p-5">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
            Upcoming refills · next 3 months
          </h2>
          <div className="flex rounded-lg border border-slate-200 bg-white p-0.5">
            <ToggleBtn active={view === "list"} onClick={() => setView("list")}>
              <List className="h-4 w-4" /> List
            </ToggleBtn>
            <ToggleBtn active={view === "calendar"} onClick={() => setView("calendar")}>
              <CalendarDays className="h-4 w-4" /> Calendar
            </ToggleBtn>
          </div>
        </div>
        {refillsLoading ? (
          <LoadingState />
        ) : refillsError ? (
          <ErrorState message="Could not load refills." onRetry={reload} />
        ) : !refills || refills.length === 0 ? (
          <EmptyState title="No refills scheduled" />
        ) : view === "calendar" ? (
          <Calendar events={events} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {refills.map((r, i) => (
              <li key={`${r.prescriptionId}-${i}`} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {r.medication} <span className="text-slate-400">·</span> {r.dosage}
                  </p>
                  <p className="text-xs text-slate-500">Refill on {formatDate(r.refillOn)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {r.overridden && <Badge color="teal">Rescheduled</Badge>}
                  <Badge color="amber">Qty {r.quantity}</Badge>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-slate-400">{label}</dt>
      <dd className="font-medium text-slate-700">{value}</dd>
    </div>
  );
}

function ToggleBtn({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active ? "bg-teal-600 text-white" : "text-slate-600 hover:bg-slate-100",
      )}
    >
      {children}
    </button>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarClock, Pill, User, ArrowRight } from "lucide-react";

import { api } from "@/lib/api";
import type { PortalSummary } from "@/lib/types";
import { formatDate, formatDateTime, repeatLabel } from "@/lib/format";
import { PortalShell } from "@/components/portal/PortalShell";
import { Card, Badge } from "@/components/ui/primitives";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/feedback";

export default function DashboardPage() {
  return (
    <PortalShell>
      <Dashboard />
    </PortalShell>
  );
}

function Dashboard() {
  const [data, setData] = useState<PortalSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const summary = await api.get<PortalSummary>("/api/me/summary");
        if (!cancelled) {
          setData(summary);
          setError(false);
        }
      } catch {
        if (!cancelled) setError(true);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  if (loading) return <LoadingState />;
  if (error) return <ErrorState message="Could not load your summary." onRetry={() => setReloadKey((k) => k + 1)} />;
  if (!data) return null;

  const { patient, upcomingAppointments, upcomingRefills } = data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-800">Welcome back, {patient.name.split(" ")[0]}</h1>
        <p className="mt-1 text-sm text-slate-500">Here is what&apos;s coming up in the next 7 days.</p>
      </div>

      <Card className="p-5">
        <div className="mb-3 flex items-center gap-2 text-slate-700">
          <User className="h-4 w-4" />
          <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Your info</h2>
        </div>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Info label="Name" value={patient.name} />
          <Info label="Email" value={patient.email} />
          <Info label="Phone" value={patient.phone ?? "—"} />
          <Info label="Date of birth" value={patient.dob ? formatDate(patient.dob) : "—"} />
        </dl>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-5">
          <SectionHeader
            icon={<CalendarClock className="h-4 w-4" />}
            title="Upcoming appointments"
            count={upcomingAppointments.length}
            href="/appointments"
          />
          {upcomingAppointments.length === 0 ? (
            <EmptyState title="No appointments in the next 7 days" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {upcomingAppointments.map((a, i) => (
                <li key={`${a.appointmentId}-${i}`} className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-800">{a.provider}</p>
                    <p className="text-xs text-slate-500">{formatDateTime(a.occursAt)}</p>
                  </div>
                  <Badge color="teal">{repeatLabel(a.repeat)}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card className="p-5">
          <SectionHeader
            icon={<Pill className="h-4 w-4" />}
            title="Refills due"
            count={upcomingRefills.length}
            href="/prescriptions"
          />
          {upcomingRefills.length === 0 ? (
            <EmptyState title="No refills due in the next 7 days" />
          ) : (
            <ul className="divide-y divide-slate-100">
              {upcomingRefills.map((r, i) => (
                <li key={`${r.prescriptionId}-${i}`} className="flex items-center justify-between py-3">
                  <div>
                    <p className="text-sm font-medium text-slate-800">
                      {r.medication} <span className="text-slate-400">·</span> {r.dosage}
                    </p>
                    <p className="text-xs text-slate-500">Refill on {formatDate(r.refillOn)}</p>
                  </div>
                  <Badge color="amber">Qty {r.quantity}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs text-slate-400">{label}</dt>
      <dd className="text-sm font-medium text-slate-700">{value}</dd>
    </div>
  );
}

function SectionHeader({
  icon,
  title,
  count,
  href,
}: {
  icon: React.ReactNode;
  title: string;
  count: number;
  href: string;
}) {
  return (
    <div className="mb-2 flex items-center justify-between">
      <div className="flex items-center gap-2 text-slate-700">
        {icon}
        <h2 className="text-sm font-semibold">{title}</h2>
        <Badge>{count}</Badge>
      </div>
      <Link href={href} className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:underline">
        View all <ArrowRight className="h-3 w-3" />
      </Link>
    </div>
  );
}

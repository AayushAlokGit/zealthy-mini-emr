"use client";

import { useState } from "react";
import useSWR from "swr";
import { parseISO } from "date-fns";
import { CalendarDays, List } from "lucide-react";

import { fetcher } from "@/lib/api";
import type { AppointmentOccurrence } from "@/lib/types";
import { formatDateTime, repeatLabel } from "@/lib/format";
import { PortalShell } from "@/components/portal/PortalShell";
import { Calendar, type CalendarEvent } from "@/components/Calendar";
import { Card, Badge } from "@/components/ui/primitives";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/feedback";
import { cn } from "@/components/ui/cn";

export default function AppointmentsPage() {
  return (
    <PortalShell>
      <Appointments />
    </PortalShell>
  );
}

function Appointments() {
  const [view, setView] = useState<"list" | "calendar">("list");
  const { data, error, isLoading, mutate } = useSWR<AppointmentOccurrence[]>(
    "/api/me/appointments",
    fetcher,
  );

  const events: CalendarEvent[] =
    data?.map((a) => ({
      date: parseISO(a.occursAt),
      title: a.provider,
      subtitle: formatDateTime(a.occursAt),
      color: "teal",
    })) ?? [];

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-800">Appointments</h1>
          <p className="mt-1 text-sm text-slate-500">Your full schedule for the next 3 months.</p>
        </div>
        <div className="flex rounded-lg border border-slate-200 bg-white p-0.5">
          <ToggleBtn active={view === "list"} onClick={() => setView("list")}>
            <List className="h-4 w-4" /> List
          </ToggleBtn>
          <ToggleBtn active={view === "calendar"} onClick={() => setView("calendar")}>
            <CalendarDays className="h-4 w-4" /> Calendar
          </ToggleBtn>
        </div>
      </div>

      <Card className="p-5">
        {isLoading ? (
          <LoadingState />
        ) : error ? (
          <ErrorState message="Could not load appointments." onRetry={() => mutate()} />
        ) : !data || data.length === 0 ? (
          <EmptyState title="No upcoming appointments" hint="Your provider will schedule these for you." />
        ) : view === "calendar" ? (
          <Calendar events={events} />
        ) : (
          <ul className="divide-y divide-slate-100">
            {data.map((a, i) => (
              <li key={`${a.appointmentId}-${i}`} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-medium text-slate-800">{a.provider}</p>
                  <p className="text-xs text-slate-500">{formatDateTime(a.occursAt)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {a.overridden && <Badge color="amber">Rescheduled</Badge>}
                  <Badge color="teal">{repeatLabel(a.repeat)}</Badge>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
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

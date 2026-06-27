"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Search, UserPlus, ChevronRight, ArrowUpDown } from "lucide-react";

import { api } from "@/lib/api";
import type { PatientListItem } from "@/lib/types";
import { formatDateTime } from "@/lib/format";
import { AdminHeader } from "@/components/admin/AdminHeader";
import { Card, Badge, Button } from "@/components/ui/primitives";
import { Input } from "@/components/ui/form";
import { LoadingState, ErrorState, EmptyState } from "@/components/ui/feedback";

type SortKey = "name" | "appointmentCount" | "prescriptionCount";

export default function AdminPatientsPage() {
  const [data, setData] = useState<PatientListItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<SortKey>("name");

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const list = await api.get<PatientListItem[]>("/api/patients");
        if (!cancelled) {
          setData(list);
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

  const rows = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    const filtered = q
      ? data.filter((p) => p.name.toLowerCase().includes(q) || p.email.toLowerCase().includes(q))
      : data;
    return [...filtered].sort((a, b) =>
      sort === "name" ? a.name.localeCompare(b.name) : b[sort] - a[sort],
    );
  }, [data, query, sort]);

  return (
    <div className="min-h-screen">
      <AdminHeader />
      <main className="mx-auto max-w-6xl px-4 py-6">
        <div className="mb-5 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-slate-800">Patients</h1>
            <p className="mt-1 text-sm text-slate-500">
              {data ? `${data.length} patient${data.length === 1 ? "" : "s"} in the system` : " "}
            </p>
          </div>
          <Link href="/admin/patients/new">
            <Button>
              <UserPlus className="h-4 w-4" /> New patient
            </Button>
          </Link>
        </div>

        <Card>
          <div className="flex flex-col gap-3 border-b border-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="relative max-w-xs flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <Input
                placeholder="Search by name or email…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <label className="flex items-center gap-2 text-sm text-slate-500">
              <ArrowUpDown className="h-4 w-4" /> Sort:
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as SortKey)}
                className="rounded-md border border-slate-300 bg-white px-2 py-1 text-sm focus:outline-none"
              >
                <option value="name">Name</option>
                <option value="appointmentCount">Appointments</option>
                <option value="prescriptionCount">Prescriptions</option>
              </select>
            </label>
          </div>

          {loading ? (
            <LoadingState />
          ) : error ? (
            <ErrorState message="Could not load patients. Is the API running?" onRetry={() => setReloadKey((k) => k + 1)} />
          ) : rows.length === 0 ? (
            <EmptyState title={query ? "No patients match your search" : "No patients yet"} />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase tracking-wide text-slate-400">
                  <tr className="border-b border-slate-100">
                    <th className="px-4 py-2.5 font-medium">Patient</th>
                    <th className="px-4 py-2.5 font-medium">Appointments</th>
                    <th className="px-4 py-2.5 font-medium">Prescriptions</th>
                    <th className="px-4 py-2.5 font-medium">Next appointment</th>
                    <th className="px-4 py-2.5" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-50">
                  {rows.map((p) => (
                    <tr key={p.id} className="group hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <Link href={`/admin/patients/${p.id}`} className="block">
                          <span className="font-medium text-slate-800">{p.name}</span>
                          <span className="block text-xs text-slate-400">{p.email}</span>
                        </Link>
                      </td>
                      <td className="px-4 py-3">
                        <Badge color="teal">{p.appointmentCount}</Badge>
                      </td>
                      <td className="px-4 py-3">
                        <Badge color="amber">{p.prescriptionCount}</Badge>
                      </td>
                      <td className="px-4 py-3 text-slate-500">
                        {p.nextAppointment ? formatDateTime(p.nextAppointment) : "—"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/admin/patients/${p.id}`}
                          className="inline-flex items-center gap-1 text-xs font-medium text-teal-600 opacity-0 transition-opacity group-hover:opacity-100"
                        >
                          Open <ChevronRight className="h-3 w-3" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </main>
    </div>
  );
}

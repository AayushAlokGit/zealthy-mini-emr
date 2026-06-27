"use client";

import { type ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import useSWR from "swr";
import { HeartPulse, LogOut } from "lucide-react";

import { api, fetcher } from "@/lib/api";
import type { Patient } from "@/lib/types";
import { LoadingState } from "@/components/ui/feedback";
import { cn } from "@/components/ui/cn";
import { NotificationBell } from "./NotificationBell";

const tabs = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/appointments", label: "Appointments" },
  { href: "/prescriptions", label: "Prescriptions" },
];

export function PortalShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  // /auth/me doubles as the auth gate: a 401 redirects to login.
  const { data: patient, error, isLoading } = useSWR<Patient>("/api/auth/me", fetcher, {
    shouldRetryOnError: false,
    onError: () => router.replace("/"),
  });

  async function logout() {
    await api.post("/api/auth/logout");
    router.replace("/");
  }

  if (isLoading) return <LoadingState label="Loading your portal…" />;
  if (error || !patient) return <LoadingState label="Redirecting to sign in…" />;

  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-teal-600 text-white">
              <HeartPulse className="h-5 w-5" />
            </div>
            <span className="font-semibold text-slate-800">Patient Portal</span>
          </div>
          <div className="flex items-center gap-1">
            <NotificationBell />
            <span className="ml-2 hidden text-sm text-slate-500 sm:inline">{patient.name}</span>
            <button
              onClick={logout}
              className="ml-1 flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-sm text-slate-500 hover:bg-slate-100"
            >
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        </div>
        <nav className="mx-auto flex max-w-5xl gap-1 px-3">
          {tabs.map((t) => {
            const active = pathname === t.href;
            return (
              <Link
                key={t.href}
                href={t.href}
                className={cn(
                  "border-b-2 px-3 py-2.5 text-sm font-medium transition-colors",
                  active
                    ? "border-teal-600 text-teal-700"
                    : "border-transparent text-slate-500 hover:text-slate-700",
                )}
              >
                {t.label}
              </Link>
            );
          })}
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">{children}</main>
    </div>
  );
}

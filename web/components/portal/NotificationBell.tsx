"use client";

import { useEffect, useState } from "react";
import { Bell, Check } from "lucide-react";

import { api } from "@/lib/api";
import type { NotificationList } from "@/lib/types";
import { formatDateTime } from "@/lib/format";

const POLL_MS = 30_000;

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<NotificationList | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const list = await api.get<NotificationList>("/api/me/notifications");
        if (!cancelled) setData(list);
      } catch {
        // keep showing the last successful fetch
      }
    }
    load();
    const id = setInterval(load, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [reloadKey]);

  const reload = () => setReloadKey((k) => k + 1);

  const unread = data?.unreadCount ?? 0;
  const items = data?.items ?? [];

  async function markAll() {
    await api.post("/api/me/notifications/read-all");
    reload();
  }

  async function markOne(id: number) {
    await api.patch(`/api/me/notifications/${id}/read`, {});
    reload();
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100"
        aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      >
        <Bell className="h-5 w-5" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
              <span className="text-sm font-semibold text-slate-700">Notifications</span>
              {unread > 0 && (
                <button
                  onClick={markAll}
                  className="flex items-center gap-1 text-xs font-medium text-teal-600 hover:underline"
                >
                  <Check className="h-3.5 w-3.5" /> Mark all read
                </button>
              )}
            </div>
            <div className="max-h-96 overflow-y-auto">
              {items.length === 0 ? (
                <p className="px-4 py-8 text-center text-sm text-slate-400">No notifications yet</p>
              ) : (
                items.map((n) => (
                  <button
                    key={n.id}
                    onClick={() => n.readAt === null && markOne(n.id)}
                    className="flex w-full gap-2 border-b border-slate-50 px-4 py-3 text-left last:border-0 hover:bg-slate-50"
                  >
                    <span
                      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                        n.readAt === null ? "bg-teal-500" : "bg-transparent"
                      }`}
                    />
                    <span className="min-w-0">
                      <span className="block text-sm text-slate-700">{n.message}</span>
                      <span className="mt-0.5 block text-xs text-slate-400">
                        {formatDateTime(n.createdAt)}
                      </span>
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { Bell, Check } from "lucide-react";

import { useNotifications } from "@/lib/NotificationsContext";
import { formatDateTime } from "@/lib/format";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { items, unreadCount, markOne, markAll } = useNotifications();

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg p-2 text-slate-500 hover:bg-slate-100"
        aria-label={`Notifications${unreadCount ? `, ${unreadCount} unread` : ""}`}
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 z-20 mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-lg">
            <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2.5">
              <span className="text-sm font-semibold text-slate-700">Notifications</span>
              {unreadCount > 0 && (
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

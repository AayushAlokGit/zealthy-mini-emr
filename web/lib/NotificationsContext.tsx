"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "./api";
import type { Notification, NotificationList } from "./types";

const POLL_MS = 30_000;

interface NotificationsValue {
  items: Notification[];
  unreadCount: number;
  reload: () => void;
  markOne: (id: number) => Promise<void>;
  markAll: () => Promise<void>;
}

/**
 * Owns the single notifications poll for the portal. Multiple components (the
 * bell, and anything else that wants the unread count) read one shared copy
 * instead of each fetching/polling independently.
 */
const NotificationsContext = createContext<NotificationsValue | null>(null);

export function NotificationsProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<NotificationList | null>(null);
  const [key, setKey] = useState(0);

  useEffect(() => {
    // `cancelled` drops a poll response that resolves after this provider
    // unmounts (or `key` changes), so it can't setState on a dead component;
    // `clearInterval` below stops the timer itself and must always run.
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
  }, [key]);

  const reload = useCallback(() => setKey((k) => k + 1), []);

  const markAll = useCallback(async () => {
    await api.post("/api/me/notifications/read-all");
    reload();
  }, [reload]);

  const markOne = useCallback(
    async (id: number) => {
      await api.patch(`/api/me/notifications/${id}/read`, {});
      reload();
    },
    [reload],
  );

  const value = useMemo<NotificationsValue>(
    () => ({
      items: data?.items ?? [],
      unreadCount: data?.unreadCount ?? 0,
      reload,
      markOne,
      markAll,
    }),
    [data, reload, markOne, markAll],
  );

  return (
    <NotificationsContext.Provider value={value}>{children}</NotificationsContext.Provider>
  );
}

export function useNotifications(): NotificationsValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) {
    throw new Error("useNotifications must be used within a NotificationsProvider");
  }
  return ctx;
}

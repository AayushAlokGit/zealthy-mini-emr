import { format, parseISO } from "date-fns";

/** Format a UTC ISO datetime in the viewer's local timezone. */
export function formatDateTime(iso: string): string {
  return format(parseISO(iso), "MMM d, yyyy 'at' h:mm a");
}

export function formatTime(iso: string): string {
  return format(parseISO(iso), "h:mm a");
}

/**
 * Format a date-only string (YYYY-MM-DD) without timezone drift.
 * `new Date("2026-07-05")` parses as UTC midnight and can shift a day in
 * negative offsets, so build the date from its parts in local time.
 */
export function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  return format(new Date(y, m - 1, d), "MMM d, yyyy");
}

export function repeatLabel(repeat: string): string {
  return { NONE: "One-time", WEEKLY: "Weekly", MONTHLY: "Monthly" }[repeat] ?? repeat;
}

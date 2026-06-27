import { format, parseISO } from "date-fns";

export function formatDateTime(iso: string): string {
  return format(parseISO(iso), "MMM d, yyyy 'at' h:mm a");
}

export function formatTime(iso: string): string {
  return format(parseISO(iso), "h:mm a");
}

// Build from parts to avoid UTC timezone drift.
export function formatDate(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  return format(new Date(y, m - 1, d), "MMM d, yyyy");
}

export function repeatLabel(repeat: string): string {
  return { NONE: "One-time", WEEKLY: "Weekly", MONTHLY: "Monthly" }[repeat] ?? repeat;
}

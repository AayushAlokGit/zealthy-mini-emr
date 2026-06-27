"use client";

import { useMemo, useState } from "react";
import {
  addMonths,
  eachDayOfInterval,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  startOfMonth,
  startOfWeek,
  subMonths,
} from "date-fns";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "./ui/cn";

export interface CalendarEvent {
  /** A Date in local time representing when the event occurs. */
  date: Date;
  title: string;
  subtitle?: string;
  color?: "teal" | "amber";
}

const dayKey = (d: Date) => format(d, "yyyy-MM-dd");
const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export function Calendar({ events }: { events: CalendarEvent[] }) {
  const [cursor, setCursor] = useState(() => startOfMonth(new Date()));
  const [selected, setSelected] = useState<Date | null>(new Date());

  const byDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const e of events) {
      const k = dayKey(e.date);
      (map.get(k) ?? map.set(k, []).get(k)!).push(e);
    }
    return map;
  }, [events]);

  const grid = useMemo(() => {
    const start = startOfWeek(startOfMonth(cursor));
    const end = endOfWeek(endOfMonth(cursor));
    return eachDayOfInterval({ start, end });
  }, [cursor]);

  const selectedEvents = selected ? byDay.get(dayKey(selected)) ?? [] : [];

  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_18rem]">
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-700">{format(cursor, "MMMM yyyy")}</h3>
          <div className="flex gap-1">
            <NavBtn label="Previous month" onClick={() => setCursor((c) => subMonths(c, 1))}>
              <ChevronLeft className="h-4 w-4" />
            </NavBtn>
            <NavBtn label="Next month" onClick={() => setCursor((c) => addMonths(c, 1))}>
              <ChevronRight className="h-4 w-4" />
            </NavBtn>
          </div>
        </div>

        <div className="grid grid-cols-7 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200 text-center">
          {WEEKDAYS.map((d) => (
            <div key={d} className="bg-slate-50 py-1.5 text-xs font-medium text-slate-400">
              {d}
            </div>
          ))}
          {grid.map((day) => {
            const dayEvents = byDay.get(dayKey(day)) ?? [];
            const inMonth = isSameMonth(day, cursor);
            const isToday = isSameDay(day, new Date());
            const isSelected = selected && isSameDay(day, selected);
            return (
              <button
                key={day.toISOString()}
                onClick={() => setSelected(day)}
                className={cn(
                  "min-h-16 bg-white p-1.5 text-left align-top transition-colors hover:bg-teal-50",
                  !inMonth && "bg-slate-50/60 text-slate-300",
                  isSelected && "ring-2 ring-inset ring-teal-500",
                )}
              >
                <span
                  className={cn(
                    "inline-flex h-5 w-5 items-center justify-center rounded-full text-xs",
                    isToday ? "bg-teal-600 font-semibold text-white" : "text-slate-600",
                    !inMonth && "text-slate-300",
                  )}
                >
                  {format(day, "d")}
                </span>
                <div className="mt-1 space-y-0.5">
                  {dayEvents.slice(0, 2).map((e, i) => (
                    <div
                      key={i}
                      className={cn(
                        "truncate rounded px-1 py-0.5 text-[10px] font-medium",
                        e.color === "amber"
                          ? "bg-amber-100 text-amber-700"
                          : "bg-teal-100 text-teal-700",
                      )}
                    >
                      {e.title}
                    </div>
                  ))}
                  {dayEvents.length > 2 && (
                    <div className="px-1 text-[10px] text-slate-400">+{dayEvents.length - 2} more</div>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
        <h4 className="text-sm font-semibold text-slate-700">
          {selected ? format(selected, "EEEE, MMM d") : "Select a day"}
        </h4>
        {selectedEvents.length === 0 ? (
          <p className="mt-3 text-xs text-slate-400">Nothing scheduled.</p>
        ) : (
          <ul className="mt-3 space-y-2">
            {selectedEvents.map((e, i) => (
              <li key={i} className="rounded-lg bg-white p-2.5 shadow-sm">
                <p className="text-sm font-medium text-slate-800">{e.title}</p>
                {e.subtitle && <p className="text-xs text-slate-500">{e.subtitle}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function NavBtn({
  children,
  onClick,
  label,
}: {
  children: React.ReactNode;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={label}
      className="rounded-md border border-slate-200 bg-white p-1.5 text-slate-500 hover:bg-slate-50"
    >
      {children}
    </button>
  );
}

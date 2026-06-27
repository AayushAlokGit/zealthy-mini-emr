import Link from "next/link";
import { Stethoscope } from "lucide-react";

export function AdminHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
        <Link href="/admin" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-800 text-white">
            <Stethoscope className="h-5 w-5" />
          </div>
          <div>
            <span className="font-semibold text-slate-800">Zealthy EMR</span>
            <span className="ml-2 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-medium uppercase text-slate-500">
              Admin
            </span>
          </div>
        </Link>
        <Link href="/" className="text-sm text-slate-500 hover:text-slate-700">
          Patient Portal →
        </Link>
      </div>
    </header>
  );
}

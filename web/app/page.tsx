"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { HeartPulse } from "lucide-react";

import { api, ApiError } from "@/lib/api";
import { loginSchema, type LoginForm } from "@/lib/schemas";
import type { Patient } from "@/lib/types";
import { Button } from "@/components/ui/primitives";
import { Field, Input } from "@/components/ui/form";

export default function LoginPage() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) });

  async function onSubmit(values: LoginForm) {
    setServerError(null);
    try {
      await api.post<Patient>("/api/auth/login", values);
      router.push("/dashboard");
    } catch (err) {
      setServerError(
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.",
      );
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-teal-600 text-white">
            <HeartPulse className="h-6 w-6" />
          </div>
          <h1 className="text-xl font-semibold text-slate-800">Patient Portal</h1>
          <p className="mt-1 text-sm text-slate-500">Sign in to view your care summary</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        >
          <Field label="Email" error={errors.email?.message}>
            <Input type="email" autoComplete="email" placeholder="you@example.com" {...register("email")} />
          </Field>
          <Field label="Password" error={errors.password?.message}>
            <Input type="password" autoComplete="current-password" placeholder="••••••••" {...register("password")} />
          </Field>

          {serverError && (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">{serverError}</p>
          )}

          <Button type="submit" loading={isSubmitting} className="w-full">
            Sign in
          </Button>

          <p className="text-center text-xs text-slate-400">
            Demo: mark@some-email-provider.net / Password123!
          </p>
        </form>

        <p className="mt-4 text-center text-sm text-slate-400">
          Staff?{" "}
          <Link href="/admin" className="font-medium text-teal-600 hover:underline">
            Open the EMR
          </Link>
        </p>
      </div>
    </main>
  );
}

"use client";

import { createContext, useContext, type ReactNode } from "react";
import type { Patient } from "./types";

/**
 * The signed-in patient, fetched once in PortalShell and shared with every
 * portal page so they don't each refetch identity. Read it with usePatient().
 */
const PatientContext = createContext<Patient | null>(null);

export function PatientProvider({
  patient,
  children,
}: {
  patient: Patient;
  children: ReactNode;
}) {
  return <PatientContext.Provider value={patient}>{children}</PatientContext.Provider>;
}

export function usePatient(): Patient {
  const patient = useContext(PatientContext);
  if (!patient) {
    throw new Error("usePatient must be used within a PatientProvider");
  }
  return patient;
}

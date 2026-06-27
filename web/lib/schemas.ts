import { z } from "zod";

const repeat = z.enum(["NONE", "WEEKLY", "MONTHLY"]);

export const patientSchema = z.object({
  name: z.string().min(1, "Name is required"),
  email: z.string().email("Enter a valid email"),
  password: z.string().min(6, "At least 6 characters"),
  dob: z.string().optional(),
  phone: z.string().optional(),
});
export type PatientForm = z.infer<typeof patientSchema>;

export const patientEditSchema = patientSchema.extend({
  password: z.string().min(6, "At least 6 characters").or(z.literal("")),
});
export type PatientEditForm = z.infer<typeof patientEditSchema>;

export const appointmentSchema = z.object({
  provider: z.string().min(1, "Provider is required"),
  startAt: z.string().min(1, "Start date/time is required"),
  repeat,
  until: z.string().optional(),
});
export type AppointmentForm = z.infer<typeof appointmentSchema>;

export const prescriptionSchema = z.object({
  medication: z.string().min(1, "Select a medication"),
  dosage: z.string().min(1, "Select a dosage"),
  quantity: z.number("Enter a quantity").int().positive("Must be greater than 0"),
  refillOn: z.string().min(1, "Refill date is required"),
  refillSchedule: repeat,
  until: z.string().optional(),
});
export type PrescriptionForm = z.infer<typeof prescriptionSchema>;

export const loginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
export type LoginForm = z.infer<typeof loginSchema>;

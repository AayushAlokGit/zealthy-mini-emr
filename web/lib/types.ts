// API types — mirror the FastAPI Pydantic schemas (camelCase via alias generator).
// The backend also exposes an OpenAPI document at `${API}/openapi.json`; these
// can be regenerated with `npm run gen:types` (see package.json).

export type Repeat = "NONE" | "WEEKLY" | "MONTHLY";

export type NotificationType =
  | "APPT_SCHEDULED"
  | "APPT_UPDATED"
  | "APPT_CANCELLED"
  | "RX_PRESCRIBED"
  | "RX_UPDATED"
  | "RX_CANCELLED";

export interface Patient {
  id: number;
  name: string;
  email: string;
  dob: string | null;
  phone: string | null;
  createdAt: string;
}

export interface PatientListItem {
  id: number;
  name: string;
  email: string;
  dob: string | null;
  phone: string | null;
  appointmentCount: number;
  prescriptionCount: number;
  nextAppointment: string | null;
}

export interface Appointment {
  id: number;
  patientId: number;
  provider: string;
  startAt: string;
  repeat: Repeat;
  until: string | null;
  createdAt: string;
}

export interface Prescription {
  id: number;
  patientId: number;
  medication: string;
  dosage: string;
  quantity: number;
  refillOn: string;
  refillSchedule: Repeat;
  until: string | null;
  createdAt: string;
}

export interface AppointmentOccurrence {
  appointmentId: number;
  provider: string;
  occursAt: string;
  repeat: Repeat;
  overridden: boolean;
}

export interface AdminOccurrence {
  appointmentId: number;
  occurrenceStart: string; // original slot — identity for editing/reverting
  occursAt: string; // effective time (after any reschedule)
  provider: string;
  repeat: Repeat;
  cancelled: boolean;
  overridden: boolean;
}

export interface OccurrenceException {
  occurrenceStart: string;
  cancelled?: boolean;
  provider?: string | null;
  startAt?: string | null;
}

export interface RefillOccurrence {
  prescriptionId: number;
  medication: string;
  dosage: string;
  quantity: number;
  refillOn: string;
  refillSchedule: Repeat;
  overridden: boolean;
}

export interface AdminRefillOccurrence {
  prescriptionId: number;
  occurrenceDate: string; // original slot — identity for editing/reverting
  refillOn: string; // effective date (after any reschedule)
  medication: string;
  dosage: string;
  quantity: number;
  refillSchedule: Repeat;
  cancelled: boolean;
  overridden: boolean;
}

export interface RefillException {
  occurrenceDate: string;
  cancelled?: boolean;
  refillOn?: string | null;
  quantity?: number | null;
}

export interface PortalSummary {
  patient: Patient;
  upcomingAppointments: AppointmentOccurrence[];
  upcomingRefills: RefillOccurrence[];
  unreadNotifications: number;
}

export interface Notification {
  id: number;
  type: NotificationType;
  message: string;
  relatedId: number | null;
  readAt: string | null;
  createdAt: string;
}

export interface NotificationList {
  items: Notification[];
  unreadCount: number;
}

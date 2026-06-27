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
}

export interface RefillOccurrence {
  prescriptionId: number;
  medication: string;
  dosage: string;
  quantity: number;
  refillOn: string;
  refillSchedule: Repeat;
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

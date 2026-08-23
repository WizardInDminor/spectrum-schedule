export type Role = "parent" | "caregiver";

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
}

export interface Child {
  id: string;
  display_name: string;
  birth_date: string | null;
  timezone: string;
}

export interface RoutineStep {
  id: string;
  position: number;
  title: string;
  icon: string | null;
  duration_minutes: number | null;
  transition_warning_minutes: number | null;
  notes: string | null;
}

export interface RoutineTemplate {
  id: string;
  child_id: string;
  name: string;
  is_active: boolean;
  steps: RoutineStep[];
}

export interface WeekdayDefaults {
  defaults: Record<string, string | null>; // "0" (Mon) … "6" (Sun) → template id
}

export interface ItemStatus {
  status: "done" | "skipped";
  event_id: string;
  occurred_at: string;
  reason: string | null;
}

export interface ScheduleItem {
  id: string;
  source_step_id: string | null;
  position: number;
  title: string;
  icon: string | null;
  planned_start: string | null; // "HH:MM:SS", child-local
  duration_minutes: number | null;
  transition_warning_minutes: number | null;
  item_status: ItemStatus | null;
}

export interface Schedule {
  id: string;
  child_id: string;
  schedule_date: string;
  template_id: string | null;
  items: ScheduleItem[];
}

export interface ScheduleEnvelope {
  schedule: Schedule | null;
  default_template_id: string | null;
}

export type PreferenceKind = "like" | "dislike" | "sensory_seeking" | "sensory_avoiding";

export interface PreferenceConfidence {
  score: number;
  label: "emerging" | "moderate" | "strong" | "mixed";
  evidence_count: number;
  last_observed: string | null;
}

export interface Preference {
  id: string;
  child_id: string;
  kind: PreferenceKind;
  category: string;
  label: string;
  context: string | null;
  confidence: PreferenceConfidence | null;
}

export interface EventOut {
  id: string;
  child_id: string;
  event_type: string;
  occurred_at: string;
  recorded_at: string;
  recorded_by: string;
  payload: Record<string, unknown>;
  tags: string[];
  corrects_event_id: string | null;
}

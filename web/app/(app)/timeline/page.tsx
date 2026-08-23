"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { EventOut, Preference } from "@/lib/types";
import styles from "./timeline.module.css";

const FILTERS: { key: string; label: string; types: string[] | null }[] = [
  { key: "all", label: "All", types: null },
  { key: "schedule", label: "Schedule", types: ["schedule_item_completed", "schedule_item_skipped"] },
  { key: "observations", label: "Observations", types: ["observation_recorded"] },
  { key: "incidents", label: "Incidents", types: ["incident_recorded"] },
  { key: "preferences", label: "Preferences", types: ["preference_evidence"] },
  { key: "notes", label: "Notes", types: ["note_added"] },
];

function eventIcon(type: string): string {
  switch (type) {
    case "schedule_item_completed":
      return "✅";
    case "schedule_item_skipped":
      return "⏭️";
    case "observation_recorded":
      return "🙂";
    case "incident_recorded":
      return "⚡";
    case "preference_evidence":
      return "❤️";
    default:
      return "📝";
  }
}

export default function TimelinePage() {
  const { activeChild } = useApp();
  const [events, setEvents] = useState<EventOut[] | null>(null);
  const [preferences, setPreferences] = useState<Preference[]>([]);
  const [filter, setFilter] = useState("all");

  const reload = useCallback(async () => {
    if (!activeChild) return;
    const [eventList, preferenceList] = await Promise.all([
      api<EventOut[]>(`/children/${activeChild.id}/events?resolved=true&limit=300`),
      api<Preference[]>(`/children/${activeChild.id}/preferences`),
    ]);
    setEvents(eventList);
    setPreferences(preferenceList);
  }, [activeChild]);

  useEffect(() => {
    reload();
  }, [reload]);

  const preferenceLabels = useMemo(
    () => Object.fromEntries(preferences.map((p) => [p.id, p.label])),
    [preferences],
  );

  const visible = useMemo(() => {
    if (!events) return [];
    const types = FILTERS.find((f) => f.key === filter)?.types;
    return types ? events.filter((e) => types.includes(e.event_type)) : events;
  }, [events, filter]);

  if (!activeChild) {
    return <p className={styles.muted}>Set up a child in Settings first.</p>;
  }

  const timeFormat = new Intl.DateTimeFormat(undefined, {
    timeZone: activeChild.timezone,
    hour: "numeric",
    minute: "2-digit",
  });
  const dayFormat = new Intl.DateTimeFormat(undefined, {
    timeZone: activeChild.timezone,
    weekday: "short",
    month: "short",
    day: "numeric",
  });

  function describe(event: EventOut): string {
    const p = event.payload;
    switch (event.event_type) {
      case "schedule_item_completed":
        return "Schedule item done";
      case "schedule_item_skipped":
        return `Skipped${p.reason ? ` — ${p.reason}` : ""}`;
      case "observation_recorded": {
        const parts: string[] = [];
        if (p.mood != null) parts.push(`mood ${p.mood}/5`);
        if (p.regulation != null) parts.push(`regulation ${p.regulation}/5`);
        if (p.sleep_hours != null) parts.push(`sleep ${p.sleep_hours}h`);
        if (p.text) parts.push(String(p.text));
        return parts.join(" · ") || "Observation";
      }
      case "incident_recorded":
        return `${p.antecedent} → ${p.behavior} → ${p.consequence} (intensity ${p.intensity}/5${
          p.duration_minutes ? `, ${p.duration_minutes} min` : ""
        })`;
      case "preference_evidence": {
        const label = preferenceLabels[String(p.preference_id)] ?? "a preference";
        const verb = p.direction === 1 ? "confirmed" : "contradicted";
        return `${verb} “${label}”${p.note ? ` — ${p.note}` : ""}`;
      }
      case "note_added":
        return String(p.text ?? "Note");
      default:
        return event.event_type;
    }
  }

  let lastDay = "";

  return (
    <div>
      <h1 className={styles.heading}>Timeline</h1>

      <div className={styles.filters} role="tablist">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            role="tab"
            aria-selected={filter === f.key}
            className={filter === f.key ? `${styles.chip} ${styles.chipActive}` : styles.chip}
            onClick={() => setFilter(f.key)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {events === null ? (
        <p className={styles.muted}>Loading…</p>
      ) : visible.length === 0 ? (
        <p className={styles.muted}>Nothing here yet.</p>
      ) : (
        <ul className={styles.list}>
          {visible.map((event) => {
            const when = new Date(event.occurred_at);
            const day = dayFormat.format(when);
            const showDay = day !== lastDay;
            lastDay = day;
            return (
              <li key={event.id}>
                {showDay && <p className={styles.day}>{day}</p>}
                <div className={styles.row}>
                  <span className={styles.rowIcon} aria-hidden>
                    {eventIcon(event.event_type)}
                  </span>
                  <div className={styles.rowText}>
                    <span className={styles.rowBody}>{describe(event)}</span>
                    <span className={styles.rowMeta}>
                      {timeFormat.format(when)}
                      {event.corrects_event_id && " · corrected"}
                      {event.tags.length > 0 && ` · ${event.tags.join(", ")}`}
                    </span>
                  </div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

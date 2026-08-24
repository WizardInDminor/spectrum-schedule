"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, todayInTimezone } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { Activity, ScheduleEnvelope } from "@/lib/types";
import { RatingScale } from "../../log/forms";
import styles from "./detail.module.css";

export default function ActivityDetailPage() {
  const { activityId } = useParams<{ activityId: string }>();
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [activity, setActivity] = useState<Activity | null>(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({
    title: "",
    icon: "",
    description: "",
    materials: "",
    skill_tags: "",
    context_tags: "",
    duration_minutes: "",
  });
  const [logging, setLogging] = useState(false);
  const [runContext, setRunContext] = useState("");
  const [rating, setRating] = useState<number | null>(null);
  const [runNote, setRunNote] = useState("");
  const [flash, setFlash] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!activeChild) return;
    const all = await api<Activity[]>(
      `/children/${activeChild.id}/activities?include_archived=true`,
    );
    setActivity(all.find((a) => a.id === activityId) ?? null);
  }, [activeChild, activityId]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (!flash) return;
    const timer = setTimeout(() => setFlash(null), 4000);
    return () => clearTimeout(timer);
  }, [flash]);

  if (!activity || !activeChild) {
    return <p className={styles.muted}>Loading…</p>;
  }

  function startEdit() {
    if (!activity) return;
    setDraft({
      title: activity.title,
      icon: activity.icon ?? "",
      description: activity.description ?? "",
      materials: activity.materials ?? "",
      skill_tags: activity.skill_tags.join(", "),
      context_tags: activity.context_tags.join(", "),
      duration_minutes: activity.duration_minutes?.toString() ?? "",
    });
    setEditing(true);
  }

  async function saveEdit(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.title.trim() || busy) return;
    setBusy(true);
    try {
      await api(`/activities/${activityId}`, {
        method: "PATCH",
        body: {
          title: draft.title.trim(),
          icon: draft.icon.trim() || null,
          description: draft.description.trim() || null,
          materials: draft.materials.trim() || null,
          skill_tags: draft.skill_tags.split(",").map((t) => t.trim()).filter(Boolean),
          context_tags: draft.context_tags.split(",").map((t) => t.trim()).filter(Boolean),
          duration_minutes: draft.duration_minutes ? Number(draft.duration_minutes) : null,
        },
      });
      setEditing(false);
      await reload();
    } finally {
      setBusy(false);
    }
  }

  async function logRun() {
    if (!activeChild || busy) return;
    setBusy(true);
    try {
      const payload: Record<string, unknown> = { activity_id: activityId };
      if (runContext.trim()) payload.context = runContext.trim();
      if (rating !== null) payload.rating = rating;
      if (runNote.trim()) payload.note = runNote.trim();
      await api(`/children/${activeChild.id}/events`, {
        method: "POST",
        body: { event_type: "activity_run", payload },
      });
      setLogging(false);
      setRating(null);
      setRunContext("");
      setRunNote("");
      setFlash("Run logged ✓");
    } finally {
      setBusy(false);
    }
  }

  async function addToToday() {
    if (!activeChild || !activity || busy) return;
    setBusy(true);
    try {
      const date = todayInTimezone(activeChild.timezone);
      let envelope = await api<ScheduleEnvelope>(
        `/children/${activeChild.id}/schedule?date=${date}`,
      );
      if (!envelope.schedule) {
        envelope = await api<ScheduleEnvelope>(`/children/${activeChild.id}/schedule`, {
          method: "POST",
          body: { schedule_date: date },
        });
      }
      if (!envelope.schedule) return;
      await api(`/schedules/${envelope.schedule.id}/items`, {
        method: "POST",
        body: {
          title: activity.title,
          icon: activity.icon,
          duration_minutes: activity.duration_minutes,
          activity_id: activity.id,
        },
      });
      setFlash("Added to today ✓");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <Link href="/activities" className={styles.back}>
        ← Activities
      </Link>

      {editing ? (
        <form className={styles.editForm} onSubmit={saveEdit}>
          <div className={styles.row}>
            <input
              className={styles.iconInput}
              maxLength={4}
              value={draft.icon}
              onChange={(e) => setDraft({ ...draft, icon: e.target.value })}
              aria-label="Icon (emoji)"
              placeholder="🎲"
            />
            <input
              className={styles.input}
              value={draft.title}
              onChange={(e) => setDraft({ ...draft, title: e.target.value })}
              required
              aria-label="Title"
            />
          </div>
          <textarea
            className={styles.textarea}
            rows={6}
            placeholder="How it works — setup, rules, variations that make it easier or harder…"
            value={draft.description}
            onChange={(e) => setDraft({ ...draft, description: e.target.value })}
          />
          <textarea
            className={styles.textarea}
            rows={2}
            placeholder="Materials (optional)"
            value={draft.materials}
            onChange={(e) => setDraft({ ...draft, materials: e.target.value })}
          />
          <input
            className={styles.input}
            placeholder="Skills, comma separated (counting, attention…)"
            value={draft.skill_tags}
            onChange={(e) => setDraft({ ...draft, skill_tags: e.target.value })}
          />
          <input
            className={styles.input}
            placeholder="Contexts, comma separated (grandparents, grocery-store, car…)"
            value={draft.context_tags}
            onChange={(e) => setDraft({ ...draft, context_tags: e.target.value })}
          />
          <input
            className={styles.input}
            type="number"
            min={1}
            placeholder="Typical minutes (optional)"
            value={draft.duration_minutes}
            onChange={(e) => setDraft({ ...draft, duration_minutes: e.target.value })}
          />
          <div className={styles.row}>
            <button className={styles.primary} disabled={busy || !draft.title.trim()}>
              Save
            </button>
            <button className={styles.secondary} type="button" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <>
          <header className={styles.header}>
            <span className={styles.bigIcon} aria-hidden>
              {activity.icon ?? "🎲"}
            </span>
            <h1 className={styles.heading}>{activity.title}</h1>
            {isParent && (
              <button className={styles.linkButton} onClick={startEdit}>
                Edit
              </button>
            )}
          </header>

          <p className={styles.tags}>
            {activity.skill_tags.map((tag) => (
              <span key={tag} className={styles.skillTag}>
                {tag}
              </span>
            ))}
            {activity.context_tags.map((tag) => (
              <span key={tag} className={styles.contextTag}>
                📍 {tag}
              </span>
            ))}
            {activity.duration_minutes && (
              <span className={styles.contextTag}>~{activity.duration_minutes} min</span>
            )}
          </p>

          {activity.description ? (
            <p className={styles.description}>{activity.description}</p>
          ) : (
            <p className={styles.muted}>No write-up yet{isParent && " — tap Edit to add one"}.</p>
          )}
          {activity.materials && (
            <p className={styles.materials}>
              <strong>Materials:</strong> {activity.materials}
            </p>
          )}

          {isParent && (
            <div className={styles.actions}>
              <button className={styles.primary} disabled={busy} onClick={() => setLogging(!logging)}>
                We did this
              </button>
              <button className={styles.secondary} disabled={busy} onClick={addToToday}>
                Add to today
              </button>
            </div>
          )}

          {logging && (
            <div className={styles.runForm}>
              <select
                className={styles.select}
                value={runContext}
                onChange={(e) => setRunContext(e.target.value)}
                aria-label="Where"
              >
                <option value="">Where? (optional)</option>
                {activity.context_tags.map((tag) => (
                  <option key={tag} value={tag}>
                    {tag}
                  </option>
                ))}
                <option value="home">home</option>
                <option value="other">other</option>
              </select>
              <RatingScale
                label="How did it go?"
                value={rating}
                onChange={setRating}
                low="rough"
                high="great"
              />
              <input
                className={styles.input}
                placeholder="Note (optional)"
                value={runNote}
                onChange={(e) => setRunNote(e.target.value)}
              />
              <button className={styles.primary} disabled={busy} onClick={logRun}>
                Log it
              </button>
            </div>
          )}
        </>
      )}

      {flash && (
        <p className={styles.flash} role="status">
          {flash}
        </p>
      )}
    </div>
  );
}

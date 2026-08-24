"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { Activity, RoutineStep, RoutineTemplate } from "@/lib/types";
import styles from "./editor.module.css";

interface StepDraft {
  title: string;
  icon: string;
  duration_minutes: string;
  transition_warning_minutes: string;
  activity_id: string; // "" = no linked activity
}

const EMPTY_DRAFT: StepDraft = {
  title: "",
  icon: "",
  duration_minutes: "",
  transition_warning_minutes: "",
  activity_id: "",
};

function draftFrom(step: RoutineStep): StepDraft {
  return {
    title: step.title,
    icon: step.icon ?? "",
    duration_minutes: step.duration_minutes?.toString() ?? "",
    transition_warning_minutes: step.transition_warning_minutes?.toString() ?? "",
    activity_id: step.activity_id ?? "",
  };
}

/** Empty inputs become explicit nulls so the API clears the field. */
function draftToPatch(draft: StepDraft): Record<string, unknown> {
  return {
    title: draft.title.trim(),
    icon: draft.icon.trim() || null,
    duration_minutes: draft.duration_minutes ? Number(draft.duration_minutes) : null,
    transition_warning_minutes: draft.transition_warning_minutes
      ? Number(draft.transition_warning_minutes)
      : null,
    activity_id: draft.activity_id || null,
  };
}

function DraftFields({
  draft,
  setDraft,
  activities,
}: {
  draft: StepDraft;
  setDraft: (d: StepDraft) => void;
  activities: Activity[];
}) {
  return (
    <>
      <div className={styles.addRow}>
        <input
          className={styles.iconInput}
          placeholder="🪥"
          maxLength={4}
          value={draft.icon}
          onChange={(e) => setDraft({ ...draft, icon: e.target.value })}
          aria-label="Icon (emoji)"
        />
        <input
          className={styles.input}
          placeholder="Step title"
          value={draft.title}
          onChange={(e) => setDraft({ ...draft, title: e.target.value })}
          required
        />
      </div>
      <div className={styles.addRow}>
        <input
          className={styles.numInput}
          type="number"
          min={1}
          placeholder="Minutes"
          value={draft.duration_minutes}
          onChange={(e) => setDraft({ ...draft, duration_minutes: e.target.value })}
          aria-label="Duration in minutes"
        />
        <input
          className={styles.numInput}
          type="number"
          min={1}
          placeholder="Warn before"
          value={draft.transition_warning_minutes}
          onChange={(e) =>
            setDraft({ ...draft, transition_warning_minutes: e.target.value })
          }
          aria-label="Transition warning minutes"
        />
      </div>
      {activities.length > 0 && (
        <select
          className={styles.activitySelect}
          value={draft.activity_id}
          onChange={(e) => setDraft({ ...draft, activity_id: e.target.value })}
          aria-label="Linked activity"
        >
          <option value="">No linked activity</option>
          {activities.map((activity) => (
            <option key={activity.id} value={activity.id}>
              {activity.icon ?? "🎲"} {activity.title}
            </option>
          ))}
        </select>
      )}
    </>
  );
}

export default function TemplateEditorPage() {
  const { templateId } = useParams<{ templateId: string }>();
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [template, setTemplate] = useState<RoutineTemplate | null>(null);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [addDraft, setAddDraft] = useState<StepDraft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<StepDraft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!activeChild) return;
    const [all, activityList] = await Promise.all([
      api<RoutineTemplate[]>(`/children/${activeChild.id}/templates`),
      api<Activity[]>(`/children/${activeChild.id}/activities`),
    ]);
    setTemplate(all.find((t) => t.id === templateId) ?? null);
    setActivities(activityList);
  }, [activeChild, templateId]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (!template) {
    return <p className={styles.muted}>Loading…</p>;
  }

  async function mutate(action: () => Promise<RoutineTemplate>) {
    setBusy(true);
    try {
      setTemplate(await action());
    } finally {
      setBusy(false);
    }
  }

  async function addStep(e: React.FormEvent) {
    e.preventDefault();
    if (!addDraft.title.trim()) return;
    const body: Record<string, unknown> = { title: addDraft.title.trim() };
    if (addDraft.icon.trim()) body.icon = addDraft.icon.trim();
    if (addDraft.duration_minutes) body.duration_minutes = Number(addDraft.duration_minutes);
    if (addDraft.transition_warning_minutes)
      body.transition_warning_minutes = Number(addDraft.transition_warning_minutes);
    if (addDraft.activity_id) body.activity_id = addDraft.activity_id;
    await mutate(() =>
      api<RoutineTemplate>(`/templates/${templateId}/steps`, { method: "POST", body }),
    );
    setAddDraft(EMPTY_DRAFT);
  }

  async function saveEdit(stepId: string) {
    if (!editDraft.title.trim()) return;
    await mutate(() =>
      api<RoutineTemplate>(`/steps/${stepId}`, {
        method: "PATCH",
        body: draftToPatch(editDraft),
      }),
    );
    setEditingId(null);
  }

  async function move(stepId: string, position: number) {
    await mutate(() =>
      api<RoutineTemplate>(`/steps/${stepId}`, { method: "PATCH", body: { position } }),
    );
  }

  async function removeStep(stepId: string) {
    await mutate(() => api<RoutineTemplate>(`/steps/${stepId}`, { method: "DELETE" }));
    if (editingId === stepId) setEditingId(null);
  }

  async function rename(name: string) {
    if (!name.trim() || name === template?.name) return;
    await mutate(() =>
      api<RoutineTemplate>(`/templates/${templateId}`, {
        method: "PATCH",
        body: { name: name.trim() },
      }),
    );
  }

  return (
    <div>
      <Link href="/routines" className={styles.back}>
        ← Routines
      </Link>
      {isParent ? (
        <input
          className={styles.titleInput}
          defaultValue={template.name}
          onBlur={(e) => rename(e.target.value)}
          aria-label="Routine name"
        />
      ) : (
        <h1 className={styles.heading}>{template.name}</h1>
      )}

      <ul className={styles.steps}>
        {template.steps.map((step, index) => (
          <li key={step.id} className={styles.stepWrap}>
            <div className={styles.step}>
              <span className={styles.stepIcon} aria-hidden>
                {step.icon ?? "▫️"}
              </span>
              <div className={styles.stepText}>
                <span className={styles.stepTitle}>{step.title}</span>
                <span className={styles.stepMeta}>
                  {step.duration_minutes && `${step.duration_minutes} min`}
                  {step.duration_minutes && step.transition_warning_minutes && " · "}
                  {step.transition_warning_minutes &&
                    `warn ${step.transition_warning_minutes} min before`}
                </span>
              </div>
              {isParent && (
                <div className={styles.stepActions}>
                  <button
                    className={styles.iconButton}
                    disabled={busy || index === 0}
                    onClick={() => move(step.id, index - 1)}
                    aria-label={`Move ${step.title} up`}
                  >
                    ↑
                  </button>
                  <button
                    className={styles.iconButton}
                    disabled={busy || index === template.steps.length - 1}
                    onClick={() => move(step.id, index + 1)}
                    aria-label={`Move ${step.title} down`}
                  >
                    ↓
                  </button>
                  <button
                    className={styles.iconButton}
                    disabled={busy}
                    onClick={() => {
                      if (editingId === step.id) {
                        setEditingId(null);
                      } else {
                        setEditingId(step.id);
                        setEditDraft(draftFrom(step));
                      }
                    }}
                    aria-label={`Edit ${step.title}`}
                  >
                    ✎
                  </button>
                </div>
              )}
            </div>
            {editingId === step.id && (
              <div className={styles.editForm}>
                <DraftFields draft={editDraft} setDraft={setEditDraft} activities={activities} />
                <div className={styles.addRow}>
                  <button
                    className={styles.primary}
                    disabled={busy || !editDraft.title.trim()}
                    onClick={() => saveEdit(step.id)}
                  >
                    Save
                  </button>
                  <button
                    className={styles.secondary}
                    disabled={busy}
                    onClick={() => setEditingId(null)}
                  >
                    Cancel
                  </button>
                  <button
                    className={styles.danger}
                    disabled={busy}
                    onClick={() => removeStep(step.id)}
                  >
                    Delete step
                  </button>
                </div>
              </div>
            )}
          </li>
        ))}
        {template.steps.length === 0 && <p className={styles.muted}>No steps yet.</p>}
      </ul>

      {isParent && (
        <form className={styles.addForm} onSubmit={addStep}>
          <h2 className={styles.subheading}>Add step</h2>
          <DraftFields draft={addDraft} setDraft={setAddDraft} activities={activities} />
          <button
            className={styles.primary}
            disabled={busy || !addDraft.title.trim()}
            type="submit"
          >
            Add
          </button>
        </form>
      )}
    </div>
  );
}

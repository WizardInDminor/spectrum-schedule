"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { RoutineTemplate } from "@/lib/types";
import styles from "./editor.module.css";

interface StepDraft {
  title: string;
  icon: string;
  duration_minutes: string;
  transition_warning_minutes: string;
}

const EMPTY_DRAFT: StepDraft = {
  title: "",
  icon: "",
  duration_minutes: "",
  transition_warning_minutes: "",
};

export default function TemplateEditorPage() {
  const { templateId } = useParams<{ templateId: string }>();
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [template, setTemplate] = useState<RoutineTemplate | null>(null);
  const [draft, setDraft] = useState<StepDraft>(EMPTY_DRAFT);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!activeChild) return;
    const all = await api<RoutineTemplate[]>(`/children/${activeChild.id}/templates`);
    setTemplate(all.find((t) => t.id === templateId) ?? null);
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
    if (!draft.title.trim()) return;
    const body: Record<string, unknown> = { title: draft.title.trim() };
    if (draft.icon.trim()) body.icon = draft.icon.trim();
    if (draft.duration_minutes) body.duration_minutes = Number(draft.duration_minutes);
    if (draft.transition_warning_minutes)
      body.transition_warning_minutes = Number(draft.transition_warning_minutes);
    await mutate(() =>
      api<RoutineTemplate>(`/templates/${templateId}/steps`, { method: "POST", body }),
    );
    setDraft(EMPTY_DRAFT);
  }

  async function move(stepId: string, position: number) {
    await mutate(() =>
      api<RoutineTemplate>(`/steps/${stepId}`, { method: "PATCH", body: { position } }),
    );
  }

  async function removeStep(stepId: string) {
    await mutate(() => api<RoutineTemplate>(`/steps/${stepId}`, { method: "DELETE" }));
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
          <li key={step.id} className={styles.step}>
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
                  onClick={() => removeStep(step.id)}
                  aria-label={`Delete ${step.title}`}
                >
                  ✕
                </button>
              </div>
            )}
          </li>
        ))}
        {template.steps.length === 0 && <p className={styles.muted}>No steps yet.</p>}
      </ul>

      {isParent && (
        <form className={styles.addForm} onSubmit={addStep}>
          <h2 className={styles.subheading}>Add step</h2>
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
            <button className={styles.primary} disabled={busy || !draft.title.trim()}>
              Add
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

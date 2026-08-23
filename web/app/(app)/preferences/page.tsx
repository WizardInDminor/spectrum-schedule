"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { Preference, PreferenceKind } from "@/lib/types";
import { KIND_ICONS, KIND_LABELS } from "../log/forms";
import styles from "./preferences.module.css";

const CATEGORIES = ["food", "sound", "texture", "activity", "place", "social", "other"];

export default function PreferencesPage() {
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [preferences, setPreferences] = useState<Preference[] | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [draft, setDraft] = useState({
    label: "",
    kind: "like" as PreferenceKind,
    category: "food",
    context: "",
  });
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!activeChild) return;
    setPreferences(await api<Preference[]>(`/children/${activeChild.id}/preferences`));
  }, [activeChild]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (!activeChild) {
    return <p className={styles.muted}>Set up a child in Settings first.</p>;
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!activeChild || !draft.label.trim()) return;
    setBusy(true);
    try {
      await api(`/children/${activeChild.id}/preferences`, {
        method: "POST",
        body: {
          label: draft.label.trim(),
          kind: draft.kind,
          category: draft.category,
          context: draft.context.trim() || null,
        },
      });
      setDraft({ ...draft, label: "", context: "" });
      setShowCreate(false);
      await reload();
    } finally {
      setBusy(false);
    }
  }

  async function logEvidence(preference: Preference, direction: 1 | -1) {
    if (!activeChild || busy) return;
    setBusy(true);
    try {
      await api(`/children/${activeChild.id}/events`, {
        method: "POST",
        body: {
          event_type: "preference_evidence",
          payload: { preference_id: preference.id, direction },
        },
      });
      await reload();
    } finally {
      setBusy(false);
    }
  }

  function bar(preference: Preference): number {
    if (!preference.confidence) return 0;
    return Math.min(Math.abs(preference.confidence.score) / 5, 1);
  }

  return (
    <div>
      <header className={styles.header}>
        <h1 className={styles.heading}>Preferences</h1>
        {isParent && (
          <button className={styles.linkButton} onClick={() => setShowCreate(!showCreate)}>
            {showCreate ? "Close" : "+ Add"}
          </button>
        )}
      </header>

      {showCreate && (
        <form className={styles.form} onSubmit={create}>
          <input
            className={styles.input}
            placeholder="Label (crunchy textures, loud hand dryers…)"
            value={draft.label}
            onChange={(e) => setDraft({ ...draft, label: e.target.value })}
            required
            autoFocus
          />
          <div className={styles.formRow}>
            <select
              className={styles.select}
              value={draft.kind}
              onChange={(e) => setDraft({ ...draft, kind: e.target.value as PreferenceKind })}
              aria-label="Kind"
            >
              {(Object.keys(KIND_ICONS) as PreferenceKind[]).map((kind) => (
                <option key={kind} value={kind}>
                  {KIND_ICONS[kind]} {kind.replace("_", " ")}
                </option>
              ))}
            </select>
            <select
              className={styles.select}
              value={draft.category}
              onChange={(e) => setDraft({ ...draft, category: e.target.value })}
              aria-label="Category"
            >
              {CATEGORIES.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>
          <input
            className={styles.input}
            placeholder="Context (optional — mealtimes, public restrooms…)"
            value={draft.context}
            onChange={(e) => setDraft({ ...draft, context: e.target.value })}
          />
          <button className={styles.primary} disabled={busy || !draft.label.trim()}>
            Add preference
          </button>
        </form>
      )}

      {preferences === null ? (
        <p className={styles.muted}>Loading…</p>
      ) : preferences.length === 0 ? (
        <p className={styles.muted}>
          Nothing recorded yet. Log evidence from the{" "}
          <Link href="/log">quick-log</Link> as you notice things.
        </p>
      ) : (
        <ul className={styles.list}>
          {preferences.map((preference) => (
            <li key={preference.id} className={styles.row}>
              <div className={styles.rowTop}>
                <span className={styles.rowKind} aria-label={KIND_LABELS[preference.kind]}>
                  {KIND_ICONS[preference.kind]}
                </span>
                <div className={styles.rowText}>
                  <span className={styles.rowLabel}>{preference.label}</span>
                  <span className={styles.rowMeta}>
                    {KIND_LABELS[preference.kind]} · {preference.category}
                    {preference.context && ` · ${preference.context}`}
                  </span>
                </div>
                {isParent && (
                  <div className={styles.rowActions}>
                    <button
                      className={styles.evidenceButton}
                      disabled={busy}
                      onClick={() => logEvidence(preference, 1)}
                      aria-label={`Confirm ${preference.label}`}
                    >
                      👍
                    </button>
                    <button
                      className={styles.evidenceButton}
                      disabled={busy}
                      onClick={() => logEvidence(preference, -1)}
                      aria-label={`Contradict ${preference.label}`}
                    >
                      👎
                    </button>
                  </div>
                )}
              </div>
              {preference.confidence ? (
                <div className={styles.confidence}>
                  <div className={styles.confidenceTrack}>
                    <div
                      className={
                        preference.confidence.score >= 0
                          ? styles.confidenceFill
                          : `${styles.confidenceFill} ${styles.confidenceNegative}`
                      }
                      style={{ width: `${bar(preference) * 100}%` }}
                    />
                  </div>
                  <span className={styles.confidenceLabel}>
                    {preference.confidence.label} · {preference.confidence.evidence_count}{" "}
                    observation{preference.confidence.evidence_count === 1 ? "" : "s"}
                  </span>
                </div>
              ) : (
                <span className={styles.confidenceLabel}>no evidence yet</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

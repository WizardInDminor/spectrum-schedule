"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { RoutineTemplate, WeekdayDefaults } from "@/lib/types";
import styles from "./routines.module.css";

const WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export default function RoutinesPage() {
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [templates, setTemplates] = useState<RoutineTemplate[] | null>(null);
  const [defaults, setDefaults] = useState<WeekdayDefaults | null>(null);
  const [newName, setNewName] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!activeChild) return;
    const [t, d] = await Promise.all([
      api<RoutineTemplate[]>(`/children/${activeChild.id}/templates`),
      api<WeekdayDefaults>(`/children/${activeChild.id}/weekday-defaults`),
    ]);
    setTemplates(t);
    setDefaults(d);
  }, [activeChild]);

  useEffect(() => {
    reload();
  }, [reload]);

  if (!activeChild) {
    return <p className={styles.muted}>Set up a child in Settings first.</p>;
  }

  async function createTemplate(e: React.FormEvent) {
    e.preventDefault();
    if (!activeChild || !newName.trim()) return;
    setBusy(true);
    try {
      await api(`/children/${activeChild.id}/templates`, {
        method: "POST",
        body: { name: newName.trim() },
      });
      setNewName("");
      await reload();
    } finally {
      setBusy(false);
    }
  }

  async function setWeekday(weekday: number, templateId: string | null) {
    if (!activeChild || !defaults) return;
    const next = { ...defaults.defaults, [String(weekday)]: templateId };
    setDefaults({ defaults: next });
    await api(`/children/${activeChild.id}/weekday-defaults`, {
      method: "PUT",
      body: { defaults: next },
    });
  }

  return (
    <div>
      <h1 className={styles.heading}>Routines</h1>

      {templates === null ? (
        <p className={styles.muted}>Loading…</p>
      ) : (
        <>
          <ul className={styles.list}>
            {templates.map((template) => (
              <li key={template.id} className={styles.row}>
                <Link href={`/routines/${template.id}`} className={styles.rowLink}>
                  <span className={styles.rowName}>
                    {template.name}
                    {!template.is_active && (
                      <span className={styles.inactive}> (inactive)</span>
                    )}
                  </span>
                  <span className={styles.rowMeta}>
                    {template.steps.length} step{template.steps.length === 1 ? "" : "s"}
                  </span>
                </Link>
              </li>
            ))}
            {templates.length === 0 && (
              <p className={styles.muted}>No routines yet.</p>
            )}
          </ul>

          {isParent && (
            <form className={styles.newForm} onSubmit={createTemplate}>
              <input
                className={styles.input}
                placeholder="New routine name (School Morning…)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
              />
              <button className={styles.primary} disabled={busy || !newName.trim()}>
                Add
              </button>
            </form>
          )}

          {defaults && templates.length > 0 && (
            <section className={styles.defaults}>
              <h2 className={styles.subheading}>Weekday defaults</h2>
              <p className={styles.hint}>
                The routine each day starts from, one tap on the Today screen.
              </p>
              <div className={styles.defaultGrid}>
                {WEEKDAYS.map((label, weekday) => (
                  <label key={label} className={styles.defaultRow}>
                    <span className={styles.defaultDay}>{label}</span>
                    <select
                      className={styles.select}
                      disabled={!isParent}
                      value={defaults.defaults[String(weekday)] ?? ""}
                      onChange={(e) => setWeekday(weekday, e.target.value || null)}
                    >
                      <option value="">—</option>
                      {templates.map((template) => (
                        <option key={template.id} value={template.id}>
                          {template.name}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
            </section>
          )}
        </>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import styles from "./log.module.css";

const COMING_LATER = [
  { icon: "🎯", label: "Trial", phase: "Phase 2" },
  { icon: "🙂", label: "Observation", phase: "Phase 3" },
  { icon: "⚡", label: "Incident", phase: "Phase 3" },
  { icon: "❤️", label: "Preference", phase: "Phase 3" },
];

export default function LogPage() {
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [text, setText] = useState("");
  const [tags, setTags] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 4000);
    return () => clearTimeout(timer);
  }, [saved]);

  if (!activeChild) {
    return <p className={styles.muted}>Set up a child in Settings first.</p>;
  }
  if (!isParent) {
    return <p className={styles.muted}>Logging is for parent accounts; caregivers have read-only access.</p>;
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!activeChild || !text.trim()) return;
    setBusy(true);
    try {
      await api(`/children/${activeChild.id}/events`, {
        method: "POST",
        body: {
          event_type: "note_added",
          payload: { text: text.trim() },
          tags: tags
            .split(",")
            .map((t) => t.trim())
            .filter(Boolean),
        },
      });
      setText("");
      setTags("");
      setSaved(true);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className={styles.heading}>Quick log</h1>

      <form className={styles.form} onSubmit={save}>
        <h2 className={styles.subheading}>📝 Note</h2>
        <textarea
          className={styles.textarea}
          placeholder="What happened?"
          rows={4}
          value={text}
          onChange={(e) => setText(e.target.value)}
          required
        />
        <input
          className={styles.input}
          placeholder="Tags, comma separated (school, mealtime…)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
        <button className={styles.primary} type="submit" disabled={busy || !text.trim()}>
          Save note
        </button>
        {saved && (
          <p className={styles.saved} role="status">
            Saved ✓
          </p>
        )}
      </form>

      <section className={styles.later}>
        <h2 className={styles.subheading}>Coming soon</h2>
        <div className={styles.laterGrid}>
          {COMING_LATER.map((entry) => (
            <div key={entry.label} className={styles.laterTile} aria-disabled>
              <span className={styles.laterIcon}>{entry.icon}</span>
              <span>{entry.label}</span>
              <span className={styles.laterPhase}>{entry.phase}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

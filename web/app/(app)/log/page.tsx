"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useApp } from "@/lib/app-context";
import {
  IncidentForm,
  NoteForm,
  ObservationForm,
  PreferenceEvidenceForm,
} from "./forms";
import styles from "./log.module.css";

type Mode = "note" | "observation" | "incident" | "preference";

const TILES: { mode: Mode; icon: string; label: string }[] = [
  { mode: "observation", icon: "🙂", label: "Observation" },
  { mode: "incident", icon: "⚡", label: "Incident" },
  { mode: "preference", icon: "❤️", label: "Preference" },
  { mode: "note", icon: "📝", label: "Note" },
];

export default function LogPage() {
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [mode, setMode] = useState<Mode | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!saved) return;
    const timer = setTimeout(() => setSaved(false), 4000);
    return () => clearTimeout(timer);
  }, [saved]);

  if (!activeChild) {
    return <p className={styles.muted}>Set up a child in Settings first.</p>;
  }
  if (!isParent) {
    return (
      <p className={styles.muted}>
        Logging is for parent accounts; caregivers have read-only access.
      </p>
    );
  }

  function onSaved() {
    setMode(null);
    setSaved(true);
  }

  return (
    <div>
      <h1 className={styles.heading}>Quick log</h1>

      {mode === null ? (
        <>
          <div className={styles.grid}>
            {TILES.map((tile) => (
              <button
                key={tile.mode}
                className={styles.tile}
                onClick={() => setMode(tile.mode)}
              >
                <span className={styles.tileIcon}>{tile.icon}</span>
                {tile.label}
              </button>
            ))}
            <div className={styles.tileDisabled} aria-disabled>
              <span className={styles.tileIcon}>🎯</span>
              Trial
              <span className={styles.tilePhase}>Phase 2</span>
            </div>
          </div>

          <nav className={styles.links}>
            <Link href="/activities" className={styles.link}>
              🎲 Activity library →
            </Link>
            <Link href="/preferences" className={styles.link}>
              ❤️ Preference list →
            </Link>
            <Link href="/timeline" className={styles.link}>
              🕒 Timeline →
            </Link>
          </nav>
        </>
      ) : mode === "note" ? (
        <NoteForm childId={activeChild.id} onSaved={onSaved} onCancel={() => setMode(null)} />
      ) : mode === "observation" ? (
        <ObservationForm
          childId={activeChild.id}
          onSaved={onSaved}
          onCancel={() => setMode(null)}
        />
      ) : mode === "incident" ? (
        <IncidentForm childId={activeChild.id} onSaved={onSaved} onCancel={() => setMode(null)} />
      ) : (
        <PreferenceEvidenceForm
          childId={activeChild.id}
          onSaved={onSaved}
          onCancel={() => setMode(null)}
        />
      )}

      {saved && (
        <p className={styles.saved} role="status">
          Saved ✓
        </p>
      )}
    </div>
  );
}

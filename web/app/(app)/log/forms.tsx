"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Preference, PreferenceKind } from "@/lib/types";
import styles from "./log.module.css";

interface FormProps {
  childId: string;
  onSaved: () => void;
  onCancel: () => void;
}

export function RatingScale({
  label,
  value,
  onChange,
  low,
  high,
}: {
  label: string;
  value: number | null;
  onChange: (v: number | null) => void;
  low: string;
  high: string;
}) {
  return (
    <div className={styles.scale}>
      <span className={styles.scaleLabel}>{label}</span>
      <div className={styles.scaleButtons} role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            className={value === n ? `${styles.scaleButton} ${styles.scaleActive}` : styles.scaleButton}
            onClick={() => onChange(value === n ? null : n)}
          >
            {n}
          </button>
        ))}
      </div>
      <span className={styles.scaleHints}>
        <span>{low}</span>
        <span>{high}</span>
      </span>
    </div>
  );
}

export function NoteForm({ childId, onSaved, onCancel }: FormProps) {
  const [text, setText] = useState("");
  const [tags, setTags] = useState("");
  const [busy, setBusy] = useState(false);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    try {
      await api(`/children/${childId}/events`, {
        method: "POST",
        body: {
          event_type: "note_added",
          payload: { text: text.trim() },
          tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        },
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={save}>
      <h2 className={styles.subheading}>📝 Note</h2>
      <textarea
        className={styles.textarea}
        placeholder="What happened?"
        rows={4}
        value={text}
        onChange={(e) => setText(e.target.value)}
        required
        autoFocus
      />
      <input
        className={styles.input}
        placeholder="Tags, comma separated (school, mealtime…)"
        value={tags}
        onChange={(e) => setTags(e.target.value)}
      />
      <div className={styles.formRow}>
        <button className={styles.primary} type="submit" disabled={busy || !text.trim()}>
          Save note
        </button>
        <button className={styles.secondary} type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function ObservationForm({ childId, onSaved, onCancel }: FormProps) {
  const [mood, setMood] = useState<number | null>(null);
  const [regulation, setRegulation] = useState<number | null>(null);
  const [sleepHours, setSleepHours] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const hasContent =
    mood !== null || regulation !== null || sleepHours !== "" || text.trim() !== "";

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!hasContent) return;
    setBusy(true);
    try {
      const payload: Record<string, unknown> = {};
      if (mood !== null) payload.mood = mood;
      if (regulation !== null) payload.regulation = regulation;
      if (sleepHours !== "") payload.sleep_hours = Number(sleepHours);
      if (text.trim()) payload.text = text.trim();
      await api(`/children/${childId}/events`, {
        method: "POST",
        body: { event_type: "observation_recorded", payload },
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={save}>
      <h2 className={styles.subheading}>🙂 Observation</h2>
      <RatingScale label="Mood" value={mood} onChange={setMood} low="rough" high="great" />
      <RatingScale
        label="Regulation"
        value={regulation}
        onChange={setRegulation}
        low="dysregulated"
        high="calm"
      />
      <label className={styles.fieldLabel}>
        Sleep last night (hours)
        <input
          className={styles.input}
          type="number"
          min={0}
          max={24}
          step={0.5}
          value={sleepHours}
          onChange={(e) => setSleepHours(e.target.value)}
        />
      </label>
      <textarea
        className={styles.textarea}
        placeholder="Anything else? (optional)"
        rows={2}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className={styles.formRow}>
        <button className={styles.primary} type="submit" disabled={busy || !hasContent}>
          Save observation
        </button>
        <button className={styles.secondary} type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export function IncidentForm({ childId, onSaved, onCancel }: FormProps) {
  const [antecedent, setAntecedent] = useState("");
  const [behavior, setBehavior] = useState("");
  const [consequence, setConsequence] = useState("");
  const [intensity, setIntensity] = useState<number | null>(null);
  const [duration, setDuration] = useState("");
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);

  const complete =
    antecedent.trim() && behavior.trim() && consequence.trim() && intensity !== null;

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!complete) return;
    setBusy(true);
    try {
      const payload: Record<string, unknown> = {
        antecedent: antecedent.trim(),
        behavior: behavior.trim(),
        consequence: consequence.trim(),
        intensity,
      };
      if (duration) payload.duration_minutes = Number(duration);
      if (location.trim()) payload.location = location.trim();
      await api(`/children/${childId}/events`, {
        method: "POST",
        body: { event_type: "incident_recorded", payload },
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className={styles.form} onSubmit={save}>
      <h2 className={styles.subheading}>⚡ Incident (A-B-C)</h2>
      <textarea
        className={styles.textarea}
        placeholder="Antecedent — what happened right before?"
        rows={2}
        value={antecedent}
        onChange={(e) => setAntecedent(e.target.value)}
        required
        autoFocus
      />
      <textarea
        className={styles.textarea}
        placeholder="Behavior — what did he do?"
        rows={2}
        value={behavior}
        onChange={(e) => setBehavior(e.target.value)}
        required
      />
      <textarea
        className={styles.textarea}
        placeholder="Consequence — what happened after / what helped?"
        rows={2}
        value={consequence}
        onChange={(e) => setConsequence(e.target.value)}
        required
      />
      <RatingScale
        label="Intensity"
        value={intensity}
        onChange={setIntensity}
        low="mild"
        high="severe"
      />
      <div className={styles.formRow}>
        <input
          className={styles.input}
          type="number"
          min={1}
          placeholder="Minutes (optional)"
          value={duration}
          onChange={(e) => setDuration(e.target.value)}
        />
        <input
          className={styles.input}
          placeholder="Where? (optional)"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
        />
      </div>
      <div className={styles.formRow}>
        <button className={styles.primary} type="submit" disabled={busy || !complete}>
          Save incident
        </button>
        <button className={styles.secondary} type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

export const KIND_ICONS: Record<PreferenceKind, string> = {
  like: "👍",
  dislike: "👎",
  sensory_seeking: "🧲",
  sensory_avoiding: "🙅",
};

export const KIND_LABELS: Record<PreferenceKind, string> = {
  like: "like",
  dislike: "dislike",
  sensory_seeking: "seeks",
  sensory_avoiding: "avoids",
};

const CATEGORIES = ["food", "sound", "texture", "activity", "place", "social", "other"];

export function PreferenceEvidenceForm({ childId, onSaved, onCancel }: FormProps) {
  const [preferences, setPreferences] = useState<Preference[] | null>(null);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Preference | null>(null);
  const [creating, setCreating] = useState(false);
  const [newKind, setNewKind] = useState<PreferenceKind>("like");
  const [newCategory, setNewCategory] = useState("food");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api<Preference[]>(`/children/${childId}/preferences`).then(setPreferences);
  }, [childId]);

  const matches = useMemo(() => {
    if (!preferences) return [];
    const q = query.trim().toLowerCase();
    return q ? preferences.filter((p) => p.label.toLowerCase().includes(q)) : preferences;
  }, [preferences, query]);

  async function logEvidence(direction: 1 | -1) {
    if (busy) return;
    setBusy(true);
    try {
      let target = selected;
      if (!target && creating && query.trim()) {
        target = await api<Preference>(`/children/${childId}/preferences`, {
          method: "POST",
          body: { kind: newKind, category: newCategory, label: query.trim() },
        });
      }
      if (!target) return;
      const payload: Record<string, unknown> = {
        preference_id: target.id,
        direction,
      };
      if (note.trim()) payload.note = note.trim();
      await api(`/children/${childId}/events`, {
        method: "POST",
        body: { event_type: "preference_evidence", payload },
      });
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  const ready = selected !== null || (creating && query.trim() !== "");

  return (
    <div className={styles.form}>
      <h2 className={styles.subheading}>❤️ Preference</h2>
      <input
        className={styles.input}
        placeholder="Search or type a new one (crunchy textures…)"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setSelected(null);
          setCreating(false);
        }}
        autoFocus
      />
      <div className={styles.prefList}>
        {matches.slice(0, 6).map((preference) => (
          <button
            key={preference.id}
            type="button"
            className={
              selected?.id === preference.id
                ? `${styles.prefOption} ${styles.prefSelected}`
                : styles.prefOption
            }
            onClick={() => {
              setSelected(preference);
              setCreating(false);
            }}
          >
            {KIND_ICONS[preference.kind]} {preference.label}
            <span className={styles.prefMeta}>{preference.category}</span>
          </button>
        ))}
        {query.trim() && !selected && (
          <button
            type="button"
            className={creating ? `${styles.prefOption} ${styles.prefSelected}` : styles.prefOption}
            onClick={() => setCreating(true)}
          >
            ＋ New: “{query.trim()}”
          </button>
        )}
      </div>
      {creating && (
        <div className={styles.formRow}>
          <select
            className={styles.select}
            value={newKind}
            onChange={(e) => setNewKind(e.target.value as PreferenceKind)}
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
            value={newCategory}
            onChange={(e) => setNewCategory(e.target.value)}
            aria-label="Category"
          >
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>
      )}
      <input
        className={styles.input}
        placeholder="Context note (optional)"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <div className={styles.formRow}>
        <button
          className={styles.evidenceYes}
          type="button"
          disabled={busy || !ready}
          onClick={() => logEvidence(1)}
        >
          👍 Confirmed it
        </button>
        <button
          className={styles.evidenceNo}
          type="button"
          disabled={busy || !ready}
          onClick={() => logEvidence(-1)}
        >
          👎 Contradicted it
        </button>
      </div>
      <button className={styles.secondary} type="button" onClick={onCancel}>
        Cancel
      </button>
    </div>
  );
}

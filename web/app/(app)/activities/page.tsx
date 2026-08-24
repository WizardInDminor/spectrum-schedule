"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { Activity } from "@/lib/types";
import styles from "./activities.module.css";

export default function ActivitiesPage() {
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [activities, setActivities] = useState<Activity[] | null>(null);
  const [query, setQuery] = useState("");
  const [context, setContext] = useState<string | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    if (!activeChild) return;
    setActivities(await api<Activity[]>(`/children/${activeChild.id}/activities`));
  }, [activeChild]);

  useEffect(() => {
    reload();
  }, [reload]);

  const contexts = useMemo(() => {
    const all = new Set<string>();
    activities?.forEach((a) => a.context_tags.forEach((t) => all.add(t)));
    return [...all].sort();
  }, [activities]);

  const visible = useMemo(() => {
    if (!activities) return [];
    const q = query.trim().toLowerCase();
    return activities.filter((activity) => {
      if (context && !activity.context_tags.includes(context)) return false;
      if (!q) return true;
      const haystack = [activity.title, ...activity.skill_tags, ...activity.context_tags]
        .join(" ")
        .toLowerCase();
      return haystack.includes(q);
    });
  }, [activities, query, context]);

  if (!activeChild) {
    return <p className={styles.muted}>Set up a child in Settings first.</p>;
  }

  async function create(e: React.FormEvent) {
    e.preventDefault();
    if (!activeChild || !newTitle.trim()) return;
    setBusy(true);
    try {
      const created = await api<Activity>(`/children/${activeChild.id}/activities`, {
        method: "POST",
        body: { title: newTitle.trim() },
      });
      setNewTitle("");
      window.location.href = `/activities/${created.id}`;
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className={styles.heading}>Activities</h1>

      {isParent && (
        <form className={styles.newForm} onSubmit={create}>
          <input
            className={styles.input}
            placeholder="New activity name (Count the cart…)"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
          />
          <button className={styles.primary} disabled={busy || !newTitle.trim()}>
            Add
          </button>
        </form>
      )}

      <input
        className={styles.search}
        placeholder="Search by name or skill (counting, attention…)"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      {contexts.length > 0 && (
        <div className={styles.chips}>
          <button
            className={context === null ? `${styles.chip} ${styles.chipActive}` : styles.chip}
            onClick={() => setContext(null)}
          >
            Anywhere
          </button>
          {contexts.map((tag) => (
            <button
              key={tag}
              className={context === tag ? `${styles.chip} ${styles.chipActive}` : styles.chip}
              onClick={() => setContext(context === tag ? null : tag)}
            >
              {tag}
            </button>
          ))}
        </div>
      )}

      {activities === null ? (
        <p className={styles.muted}>Loading…</p>
      ) : visible.length === 0 ? (
        <p className={styles.muted}>
          {activities.length === 0
            ? "No activities yet — add the first game above."
            : "Nothing matches that filter."}
        </p>
      ) : (
        <ul className={styles.list}>
          {visible.map((activity) => (
            <li key={activity.id}>
              <Link href={`/activities/${activity.id}`} className={styles.row}>
                <span className={styles.rowIcon} aria-hidden>
                  {activity.icon ?? "🎲"}
                </span>
                <div className={styles.rowText}>
                  <span className={styles.rowTitle}>{activity.title}</span>
                  <span className={styles.rowMeta}>
                    {activity.skill_tags.join(", ")}
                    {activity.skill_tags.length > 0 && activity.context_tags.length > 0 && " · "}
                    {activity.context_tags.join(", ")}
                    {activity.duration_minutes && ` · ~${activity.duration_minutes} min`}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

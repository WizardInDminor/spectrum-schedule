"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  api,
  formatTime,
  minutesNowInTimezone,
  timeToMinutes,
  todayInTimezone,
} from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { EventOut, ScheduleEnvelope, ScheduleItem } from "@/lib/types";
import styles from "./today.module.css";

interface Toast {
  message: string;
  undoEventId: string | null;
}

export default function TodayPage() {
  const { me, activeChild } = useApp();
  const isParent = me.role === "parent";
  const [envelope, setEnvelope] = useState<ScheduleEnvelope | null>(null);
  const [toast, setToast] = useState<Toast | null>(null);
  const [skipTarget, setSkipTarget] = useState<string | null>(null);
  const [skipReason, setSkipReason] = useState("");
  const [nowMinutes, setNowMinutes] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const date = activeChild ? todayInTimezone(activeChild.timezone) : null;

  const reload = useCallback(async () => {
    if (!activeChild || !date) return;
    setEnvelope(
      await api<ScheduleEnvelope>(`/children/${activeChild.id}/schedule?date=${date}`),
    );
  }, [activeChild, date]);

  useEffect(() => {
    reload();
  }, [reload]);

  useEffect(() => {
    if (!activeChild) return;
    const tick = () => setNowMinutes(minutesNowInTimezone(activeChild.timezone));
    tick();
    const interval = setInterval(tick, 30_000);
    return () => clearInterval(interval);
  }, [activeChild]);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 6000);
    return () => clearTimeout(timer);
  }, [toast]);

  const schedule = envelope?.schedule ?? null;
  const pending = useMemo(
    () => schedule?.items.filter((i) => !i.item_status) ?? [],
    [schedule],
  );
  const finished = useMemo(
    () => schedule?.items.filter((i) => i.item_status) ?? [],
    [schedule],
  );

  const warning = useMemo(() => {
    if (nowMinutes === null) return null;
    for (const item of pending) {
      if (!item.planned_start || !item.duration_minutes || !item.transition_warning_minutes)
        continue;
      const end = timeToMinutes(item.planned_start) + item.duration_minutes;
      if (nowMinutes >= end - item.transition_warning_minutes && nowMinutes < end) {
        const index = pending.indexOf(item);
        return { item, next: pending[index + 1] ?? null };
      }
    }
    return null;
  }, [pending, nowMinutes]);

  if (!activeChild) {
    return (
      <div className={styles.empty}>
        <h1 className={styles.heading}>Today</h1>
        <p>
          No child set up yet.{" "}
          {isParent ? <Link href="/settings">Add one in Settings.</Link> : "Ask a parent to add one."}
        </p>
      </div>
    );
  }

  async function appendStatusEvent(item: ScheduleItem, type: string, reason?: string) {
    if (!activeChild || busy) return;
    setBusy(true);
    try {
      const payload: Record<string, unknown> = {
        schedule_item_id: item.id,
        planned_date: date,
      };
      if (reason) payload.reason = reason;
      const event = await api<EventOut>(`/children/${activeChild.id}/events`, {
        method: "POST",
        body: { event_type: type, payload },
      });
      setToast({
        message: type === "schedule_item_completed" ? `${item.title} done` : `${item.title} skipped`,
        undoEventId: event.id,
      });
      await reload();
    } finally {
      setBusy(false);
      setSkipTarget(null);
      setSkipReason("");
    }
  }

  async function undo(eventId: string) {
    await api(`/events/${eventId}/correct`, { method: "POST", body: { retracted: true } });
    setToast(null);
    await reload();
  }

  async function generate() {
    if (!activeChild || busy) return;
    setBusy(true);
    try {
      await api(`/children/${activeChild.id}/schedule`, {
        method: "POST",
        body: { schedule_date: date },
      });
      await reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <header className={styles.header}>
        <h1 className={styles.heading}>Today</h1>
        {isParent && schedule && (
          <button className={styles.linkButton} onClick={generate} disabled={busy}>
            Regenerate
          </button>
        )}
      </header>

      {warning && (
        <div className={styles.warningBanner} role="alert">
          ⏳ <strong>{warning.item.title}</strong> is wrapping up
          {warning.next && (
            <>
              {" "}
              — then <strong>{warning.next.title}</strong>
            </>
          )}
        </div>
      )}

      {!envelope ? (
        <p className={styles.muted}>Loading…</p>
      ) : !schedule ? (
        <div className={styles.empty}>
          <p className={styles.muted}>No schedule for today yet.</p>
          {isParent && (
            <button className={styles.primary} onClick={generate} disabled={busy}>
              {envelope.default_template_id
                ? "Start today's routine"
                : "Start an empty day"}
            </button>
          )}
        </div>
      ) : (
        <>
          {pending.length === 0 && (
            <p className={styles.allDone}>All done for today 🎉</p>
          )}
          <ul className={styles.list}>
            {pending.map((item, index) => (
              <li
                key={item.id}
                className={index === 0 ? `${styles.card} ${styles.now}` : styles.card}
              >
                {index === 0 && <span className={styles.nowLabel}>Now</span>}
                {index === 1 && <span className={styles.thenLabel}>Then</span>}
                <div className={styles.cardBody}>
                  <span className={styles.cardIcon} aria-hidden>
                    {item.icon ?? "▫️"}
                  </span>
                  <div className={styles.cardText}>
                    <span className={styles.cardTitle}>{item.title}</span>
                    <span className={styles.cardMeta}>
                      {item.planned_start && formatTime(item.planned_start)}
                      {item.planned_start && item.duration_minutes && " · "}
                      {item.duration_minutes && `${item.duration_minutes} min`}
                    </span>
                  </div>
                  {isParent && (
                    <div className={styles.cardActions}>
                      <button
                        className={styles.doneButton}
                        disabled={busy}
                        onClick={() => appendStatusEvent(item, "schedule_item_completed")}
                        aria-label={`Mark ${item.title} done`}
                      >
                        ✓
                      </button>
                      <button
                        className={styles.skipButton}
                        disabled={busy}
                        onClick={() =>
                          setSkipTarget(skipTarget === item.id ? null : item.id)
                        }
                        aria-label={`Skip ${item.title}`}
                      >
                        Skip
                      </button>
                    </div>
                  )}
                </div>
                {skipTarget === item.id && (
                  <div className={styles.skipForm}>
                    <input
                      className={styles.skipInput}
                      placeholder="Reason (optional)"
                      value={skipReason}
                      onChange={(e) => setSkipReason(e.target.value)}
                    />
                    <button
                      className={styles.skipConfirm}
                      disabled={busy}
                      onClick={() =>
                        appendStatusEvent(
                          item,
                          "schedule_item_skipped",
                          skipReason.trim() || undefined,
                        )
                      }
                    >
                      Skip it
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>

          {finished.length > 0 && (
            <section>
              <h2 className={styles.subheading}>Finished</h2>
              <ul className={styles.list}>
                {finished.map((item) => (
                  <li key={item.id} className={styles.slimRow}>
                    <span className={styles.slimStatus} aria-hidden>
                      {item.item_status?.status === "done" ? "✅" : "⏭️"}
                    </span>
                    <span className={styles.slimTitle}>{item.title}</span>
                    {item.item_status?.reason && (
                      <span className={styles.slimReason}>{item.item_status.reason}</span>
                    )}
                    {isParent && item.item_status && (
                      <button
                        className={styles.linkButton}
                        onClick={() => undo(item.item_status!.event_id)}
                      >
                        Undo
                      </button>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}

      {toast && (
        <div className={styles.toast} role="status">
          {toast.message}
          {toast.undoEventId && (
            <button className={styles.toastUndo} onClick={() => undo(toast.undoEventId!)}>
              Undo
            </button>
          )}
        </div>
      )}
    </div>
  );
}

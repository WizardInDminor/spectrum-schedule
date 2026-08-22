"use client";

import { useEffect, useState } from "react";
import styles from "./health-status.module.css";

type State = "checking" | "ok" | "error";

export function HealthStatus() {
  const [state, setState] = useState<State>("checking");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => res.json())
      .then((body) => setState(body.status === "ok" ? "ok" : "error"))
      .catch(() => setState("error"));
  }, []);

  const label =
    state === "checking"
      ? "Checking API…"
      : state === "ok"
        ? "API connected"
        : "API unreachable";

  return (
    <p className={`${styles.badge} ${styles[state]}`} role="status">
      {label}
    </p>
  );
}

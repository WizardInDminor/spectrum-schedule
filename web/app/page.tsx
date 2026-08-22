import styles from "./page.module.css";
import { HealthStatus } from "./health-status";

export default function Home() {
  return (
    <main className={styles.main}>
      <h1 className={styles.title}>Spectrum Schedule</h1>
      <p className={styles.tagline}>
        Daily schedule &amp; developmental tracker — scaffold. See{" "}
        <code>SPEC.md</code> for what comes next.
      </p>
      <HealthStatus />
    </main>
  );
}

"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./TabNav.module.css";

const TABS = [
  { href: "/", label: "Today", icon: "📅" },
  { href: "/log", label: "Log", icon: "✏️" },
  { href: "/routines", label: "Routines", icon: "🔁" },
  { href: "/settings", label: "Settings", icon: "⚙️" },
];

export function TabNav() {
  const pathname = usePathname();
  return (
    <nav className={styles.nav} aria-label="Main">
      {TABS.map((tab) => {
        const active =
          tab.href === "/" ? pathname === "/" : pathname.startsWith(tab.href);
        return (
          <Link
            key={tab.href}
            href={tab.href}
            className={active ? `${styles.tab} ${styles.active}` : styles.tab}
            aria-current={active ? "page" : undefined}
          >
            <span className={styles.icon} aria-hidden>
              {tab.icon}
            </span>
            {tab.label}
          </Link>
        );
      })}
    </nav>
  );
}

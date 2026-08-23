"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { AppContext } from "@/lib/app-context";
import type { Child, User } from "@/lib/types";
import { TabNav } from "@/components/TabNav";
import styles from "./layout.module.css";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [me, setMe] = useState<User | null>(null);
  const [kids, setKids] = useState<Child[] | null>(null);

  const reloadKids = useCallback(async () => {
    setKids(await api<Child[]>("/children"));
  }, []);

  useEffect(() => {
    api<User>("/auth/me")
      .then((user) => {
        setMe(user);
        return reloadKids();
      })
      .catch(() => router.replace("/login"));
  }, [router, reloadKids]);

  if (!me || kids === null) {
    return <p className={styles.loading}>Loading…</p>;
  }

  return (
    <AppContext.Provider
      value={{ me, kids, activeChild: kids[0] ?? null, reloadKids }}
    >
      <div className={styles.shell}>
        <main className={styles.main}>{children}</main>
        <TabNav />
      </div>
    </AppContext.Provider>
  );
}

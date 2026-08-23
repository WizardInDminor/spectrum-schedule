"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import type { Child, User } from "@/lib/types";
import styles from "./settings.module.css";

export default function SettingsPage() {
  const router = useRouter();
  const { me, kids, reloadKids } = useApp();
  const isParent = me.role === "parent";

  const [users, setUsers] = useState<User[] | null>(null);
  const [childForm, setChildForm] = useState({ display_name: "", timezone: "", birth_date: "" });
  const [userForm, setUserForm] = useState({
    email: "",
    display_name: "",
    password: "",
    role: "parent",
  });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reloadUsers = useCallback(async () => {
    if (!isParent) return;
    setUsers(await api<User[]>("/users"));
  }, [isParent]);

  useEffect(() => {
    reloadUsers();
  }, [reloadUsers]);

  useEffect(() => {
    setChildForm((form) =>
      form.timezone ? form : { ...form, timezone: Intl.DateTimeFormat().resolvedOptions().timeZone },
    );
  }, []);

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? String(err.message) : "Something went wrong.");
    } finally {
      setBusy(false);
    }
  }

  async function addChild(e: React.FormEvent) {
    e.preventDefault();
    await run(async () => {
      await api<Child>("/children", {
        method: "POST",
        body: {
          display_name: childForm.display_name.trim(),
          timezone: childForm.timezone.trim(),
          birth_date: childForm.birth_date || null,
        },
      });
      setChildForm({ display_name: "", timezone: childForm.timezone, birth_date: "" });
      await reloadKids();
    });
  }

  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    await run(async () => {
      await api<User>("/users", {
        method: "POST",
        body: {
          email: userForm.email.trim(),
          display_name: userForm.display_name.trim(),
          password: userForm.password,
          role: userForm.role,
        },
      });
      setUserForm({ email: "", display_name: "", password: "", role: "parent" });
      await reloadUsers();
    });
  }

  async function toggleActive(user: User) {
    await run(async () => {
      await api(`/users/${user.id}`, {
        method: "PATCH",
        body: { is_active: !user.is_active },
      });
      await reloadUsers();
    });
  }

  async function logout() {
    await api("/auth/logout", { method: "POST" });
    router.replace("/login");
  }

  return (
    <div>
      <h1 className={styles.heading}>Settings</h1>

      <section className={styles.section}>
        <h2 className={styles.subheading}>Account</h2>
        <p className={styles.accountRow}>
          {me.display_name} · {me.email} · {me.role}
        </p>
        <button className={styles.secondary} onClick={logout}>
          Sign out
        </button>
      </section>

      <section className={styles.section}>
        <h2 className={styles.subheading}>Children</h2>
        <ul className={styles.list}>
          {kids.map((child) => (
            <li key={child.id} className={styles.row}>
              <span className={styles.rowName}>{child.display_name}</span>
              <span className={styles.rowMeta}>{child.timezone}</span>
            </li>
          ))}
          {kids.length === 0 && <p className={styles.muted}>No children yet.</p>}
        </ul>
        {isParent && (
          <form className={styles.form} onSubmit={addChild}>
            <input
              className={styles.input}
              placeholder="Name"
              value={childForm.display_name}
              onChange={(e) => setChildForm({ ...childForm, display_name: e.target.value })}
              required
            />
            <div className={styles.formRow}>
              <input
                className={styles.input}
                placeholder="IANA timezone"
                value={childForm.timezone}
                onChange={(e) => setChildForm({ ...childForm, timezone: e.target.value })}
                required
              />
              <input
                className={styles.input}
                type="date"
                value={childForm.birth_date}
                onChange={(e) => setChildForm({ ...childForm, birth_date: e.target.value })}
                aria-label="Birth date (optional)"
              />
            </div>
            <button className={styles.primary} disabled={busy || !childForm.display_name.trim()}>
              Add child
            </button>
          </form>
        )}
      </section>

      {isParent && (
        <section className={styles.section}>
          <h2 className={styles.subheading}>Users</h2>
          <ul className={styles.list}>
            {(users ?? []).map((user) => (
              <li key={user.id} className={styles.row}>
                <span className={styles.rowName}>
                  {user.display_name}
                  {!user.is_active && <span className={styles.muted}> (deactivated)</span>}
                </span>
                <span className={styles.rowMeta}>{user.role}</span>
                {user.id !== me.id && (
                  <button
                    className={styles.linkButton}
                    disabled={busy}
                    onClick={() => toggleActive(user)}
                  >
                    {user.is_active ? "Deactivate" : "Reactivate"}
                  </button>
                )}
              </li>
            ))}
          </ul>
          <form className={styles.form} onSubmit={addUser}>
            <input
              className={styles.input}
              type="email"
              placeholder="Email"
              value={userForm.email}
              onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
              required
            />
            <div className={styles.formRow}>
              <input
                className={styles.input}
                placeholder="Display name"
                value={userForm.display_name}
                onChange={(e) => setUserForm({ ...userForm, display_name: e.target.value })}
                required
              />
              <select
                className={styles.select}
                value={userForm.role}
                onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
              >
                <option value="parent">parent</option>
                <option value="caregiver">caregiver</option>
              </select>
            </div>
            <input
              className={styles.input}
              type="password"
              placeholder="Password (min 8 chars)"
              minLength={8}
              value={userForm.password}
              onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
              required
            />
            <button className={styles.primary} disabled={busy}>
              Add user
            </button>
          </form>
        </section>
      )}

      {error && <p className={styles.error}>{error}</p>}
    </div>
  );
}

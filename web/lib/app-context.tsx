"use client";

import { createContext, useContext } from "react";
import type { Child, User } from "./types";

export interface AppState {
  me: User;
  kids: Child[];
  activeChild: Child | null;
  reloadKids: () => Promise<void>;
}

export const AppContext = createContext<AppState | null>(null);

export function useApp(): AppState {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used inside the app shell");
  return value;
}

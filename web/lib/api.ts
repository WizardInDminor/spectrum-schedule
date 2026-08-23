interface ValidationItem {
  loc?: (string | number)[];
  msg?: string;
}

/** Turn a FastAPI error detail into something a form can show a human. */
function detailToMessage(status: number, detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const parts = (detail as ValidationItem[])
      .map((item) => {
        const field = item.loc?.filter((p) => p !== "body").join(".");
        const msg = item.msg?.replace(/^Value error, /, "") ?? "invalid value";
        return field ? `${field}: ${msg}` : msg;
      })
      .filter(Boolean);
    if (parts.length > 0) return parts.join("; ");
  }
  return `Request failed (${status})`;
}

export class ApiError extends Error {
  status: number;
  detail: unknown;

  constructor(status: number, detail: unknown) {
    super(detailToMessage(status, detail));
    this.status = status;
    this.detail = detail;
  }
}

function csrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

export async function api<T>(
  path: string,
  opts: { method?: string; body?: unknown } = {},
): Promise<T> {
  const method = opts.method ?? "GET";
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET" && method !== "HEAD") {
    const token = csrfToken();
    if (token) headers["X-CSRF-Token"] = token;
  }

  const response = await fetch(`/api/v1${path}`, {
    method,
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });

  if (response.status === 401 && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
  if (!response.ok) {
    let detail: unknown = null;
    try {
      detail = (await response.json()).detail;
    } catch {
      // non-JSON error body
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Today's date (YYYY-MM-DD) in an IANA timezone — schedule dates live in the
 * child's timezone, not the browser's. */
export function todayInTimezone(timeZone: string): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone }).format(new Date());
}

/** Minutes since local midnight in an IANA timezone. */
export function minutesNowInTimezone(timeZone: string): number {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).formatToParts(new Date());
  const hour = Number(parts.find((p) => p.type === "hour")?.value ?? 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value ?? 0);
  return hour * 60 + minute;
}

export function timeToMinutes(hhmmss: string): number {
  const [hours, minutes] = hhmmss.split(":").map(Number);
  return hours * 60 + minutes;
}

export function formatTime(hhmmss: string): string {
  const [hours, minutes] = hhmmss.split(":").map(Number);
  const suffix = hours >= 12 ? "pm" : "am";
  const displayHours = hours % 12 === 0 ? 12 : hours % 12;
  return `${displayHours}:${String(minutes).padStart(2, "0")}${suffix}`;
}

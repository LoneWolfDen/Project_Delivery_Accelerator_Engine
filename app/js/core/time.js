// Timestamps (DAT-02): ISO 8601 UTC strings with milliseconds, e.g. '2026-10-04T09:12:00.000Z'.
export function nowIso() {
  return new Date().toISOString();
}

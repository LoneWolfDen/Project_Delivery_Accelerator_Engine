// Record IDs (DAT-02): '<prefix>_<uuid>', e.g. 'prj_3f2a…'. Matches the diagnostics ID pattern.
const PREFIX_RE = /^[a-z]{2,8}$/;

export function newId(prefix) {
  if (!PREFIX_RE.test(prefix)) throw new TypeError(`invalid id prefix: ${String(prefix)}`);
  return `${prefix}_${crypto.randomUUID()}`;
}

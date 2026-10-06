// Error catalogue (DGN-01; TARGET_ARCHITECTURE.md §22). Every visible error and every log
// event uses one of these stable codes. Titles and help are plain language for non-technical users.

const entries = [
  ['APP-UNEXPECTED', 'Something went wrong', 'The app hit an unexpected problem. Your saved work is not affected. Reload the page; if this keeps happening, copy the diagnostic code and send it to whoever supports the app.'],
  ['STO-OPEN-FAIL', 'Your saved data could not be opened', "The browser didn't let the app open its storage. Close other tabs of this app and reload. Private or guest windows may block storage."],
  ['STO-QUOTA', 'Storage is full', 'The browser has no more room for this app. Download a backup, then remove projects or files you no longer need from Trash.'],
  ['STO-WRITE-FAIL', 'A change could not be saved', 'The last change was not saved. Try again; if it fails again, download a backup and reload the page.'],
  ['STO-NEWER-VERSION', 'Your data is read-only in this version', 'Data was saved by a newer version of this app, so this version opens it read-only: you can look at it and download a backup, but nothing will be changed. Use the newer version to keep working.'],
  ['STO-BLOCKED', 'Close other tabs of this app', 'Another tab of this app is still open with an older version. Close it (or reload it) so this tab can finish starting.'],
  ['STO-CONFLICT', 'This was changed somewhere else', 'Another tab or window changed this after you opened it, so your change was not saved (nothing was overwritten). Reload to see the latest version, then make your change again.'],
  ['STO-INVALID', 'Some saved data could not be read', 'A record did not pass its safety checks, so it was not used or saved. Nothing was deleted. If this keeps happening, copy the diagnostic code for support.'],
  ['MIG-FAIL', 'Your data could not be upgraded', 'The app could not upgrade your saved data to this version. Nothing was changed. Download a backup and contact support with the diagnostic code.'],
  ['IMP-READ-FAIL', 'A file could not be read', 'The browser could not read the file. Check that it is not open in another program or stored online-only, then try again.'],
  ['IMP-PARSE-FAIL', 'A file could not be understood', 'The file looks damaged or is in a format the app does not support. Try saving it again as .txt, .md, .csv or .docx.'],
  ['BAK-INVALID', 'This backup file cannot be used', 'The file is not a valid backup from this app, or it was changed after it was made. Nothing was restored.'],
  ['AI-NET', 'The AI service could not be reached', 'Check your internet connection. Your organisation may also block this service. Nothing was sent.'],
  ['AI-HTTP', 'The AI service returned an error', 'The AI service refused the request. Check your key and try again later. Your documents were not changed.'],
];

export const ERRORS = Object.freeze(
  Object.fromEntries(entries.map(([code, title, help]) => [code, Object.freeze({ code, title, help })])),
);

export function isErrorCode(code) {
  return Object.prototype.hasOwnProperty.call(ERRORS, code);
}

// Catalogue entry for a code; unknown codes fall back to APP-UNEXPECTED.
export function getError(code) {
  return isErrorCode(code) ? ERRORS[code] : ERRORS['APP-UNEXPECTED'];
}

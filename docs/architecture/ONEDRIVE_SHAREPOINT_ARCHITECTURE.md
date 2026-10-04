# OneDrive and SharePoint Architecture

| Field | Value |
|---|---|
| Status | Proposed. V1 and V2 can be built without approvals. V3 is blocked on external prerequisites (§5). |
| Date | 2026-10-04 |
| Parent | `TARGET_ARCHITECTURE.md` §9–12, §16–17 |
| Current state | No OneDrive, SharePoint, Graph or MSAL code exists. Legacy input is upload or arbitrary server path (security H-4); legacy output is draw.io download only (`CURRENT_IMPLEMENTATION_ASSESSMENT.md` §5–6). |

Principle: **the app touches only files the user explicitly chooses, and writes only where the user explicitly chooses.** It never scans disks, never uploads in the background, and never hard-codes a drive or site.

---

## 1. Connector interfaces

From `TARGET_ARCHITECTURE.md` §17:

```
SourceConnector      { id, label, isAvailable(), pick(options) → FileRef[], read(ref) → {blob, meta}, changedSince?(refs) }
DestinationConnector { id, label, isAvailable(), chooseDestination(suggestedName) → DestRef, write(destRef, blob, {ifMatch?}) → result }
```

| Level | Source connector | Destination connector |
|---|---|---|
| V1 | `source-local`: `<input type=file multiple>` and drag-and-drop | `dest-download`: Blob URL with `<a download>` |
| V2 | `source-folder`: `showDirectoryPicker()` handle (Chromium) | `dest-save-picker`: `showSaveFilePicker()` (Chromium) |
| V3 | `graph-picker-source`: Microsoft File Picker | `graph-dest`: Graph upload to a picked folder |

All levels feed the same import pipeline (preview → keep → provenance) and the same export builders.

## 2. Input

### V1: user-selected local or synced files (no approvals needed)

- **Mechanism:** standard file input (`multiple`, `accept` = supported types) and a drop zone. Works in every target browser.
- **OneDrive/SharePoint use:** the user's OneDrive client syncs a library to a local folder (e.g. `OneDrive - <Org>/Project X`), and the user picks files from it in the normal dialog. The browser receives only those files.
- **Files On-Demand:** cloud-only placeholders are downloaded by the OS when the browser reads them. If a read fails, show `IMP-READ-FAIL` with "If this file is in OneDrive, right-click → Always keep on this device, then try again."
- **Preview before retention:** each file is parsed in memory and shown as a preview card: name, size, detected type, as-of date, first sections, number of chunks and detected items, warnings (e.g. "scanned PDF, no text found"). The user picks **Keep** or **Discard** per file. Nothing is written before Keep.
- **Duplicate check:** the same SHA-256 in the same project shows "Already imported on 2 Oct (Source 4). Skip / Import as a new version of that source."
- **Provenance:** `sourceSystem: "local-file"`. The app can't reliably tell a OneDrive-synced path from a plain local one (browsers expose no path), so the user may tick "This came from OneDrive/SharePoint" and optionally paste the web link. This is stored as user-entered provenance, labelled as such.
- **Limits:** a per-file size warning above 25 MB (setting) and a hard stop above 100 MB, with plain-language reasons.

### V2: user-selected folder with user-triggered refresh (Chromium only, browser policy permitting)

- **Availability:** `'showDirectoryPicker' in window` and not blocked by policy. If unavailable, the button is hidden and V1 is used, with the note "Folder selection isn't available in this browser; choose files instead."
- **Flow:**
  1. The user clicks **Link a folder** and picks one folder (e.g. a synced SharePoint library folder).
  2. The handle is stored in IndexedDB (`folderLinks` store added by a migration) with the user's label.
  3. **Refresh is user-triggered only** (button), never on a timer and never at start-up.
  4. On Refresh: `handle.requestPermission({mode: "read"})` (browser prompt as needed). Then list **only that folder** (one level by default; "include sub-folders" is an explicit option, depth-limited to 3, with a file-count cap of 500).
  5. Compute a changed-file preview against stored provenance: **New**, **Changed** (`lastModified` or size differs, confirmed by hashing), **Missing**, **Unchanged**. The user ticks which to import.
  6. Changed files create a **new Source version** (`supersedesSourceId`), never an overwrite. Missing files are reported only, never deleted from the project.
- **Provenance:** `sourceSystem: "synced-folder"`, `relativePath` inside the linked folder, plus the folder link label.
- **Revocation:** **Unlink folder** deletes the stored handle. Browser site settings can also revoke it.

### V3: Microsoft File Picker or Graph (requires approvals)

- **Mechanism:** Microsoft File Picker (OneDrive/SharePoint picker v8) or Graph `driveItem` reads, using delegated tokens from MSAL.js (auth code plus PKCE).
- **User experience:** "Choose from OneDrive or SharePoint" opens the Microsoft picker; the user selects files; the app receives item references and downloads only those items' content.
- **Provenance:** `sourceSystem: "graph"`, `driveId`, `itemId`, `webUrl`, `eTag`, `lastModifiedDateTime`, `lastModifiedBy` (display name only if the user agrees to store it).
- **Refresh:** user-triggered. Compare `eTag` / `cTag`, then use the same New / Changed / Missing preview as V2.
- **Least privilege:** the scopes are to be agreed with the tenant administrator (§5). Prefer the narrowest delegated scope that supports the picker and reading selected items. Never application permissions, and never tenant-wide `Sites.Read.All` unless the administrator mandates it.

## 3. Output

### V1: download, then the user saves (no approvals needed)

- **Exports:** project report (HTML, printable to PDF by the browser), Markdown, JSON with manifest, Copilot package (`COPILOT_AND_CHAT_ARCHITECTURE.md` §6), backup file.
- **Manifest:** every export includes `manifest.json` with app version, export time, project, the list of included sources (name, SHA-256, as-of date), item and review counts, and an SHA-256 per file.
- **Mechanism:** a Blob download. The browser's download setting decides whether a Save dialog appears.
- **Boundary notice**, shown before the first export of each session, with a "don't show again this session" option:
  > "You're about to save project content as a file. If you save it into a OneDrive or SharePoint folder, it will be copied to Microsoft 365 and follow that location's sharing and retention rules."

### V2: browser-supported save workflow (Chromium)

- `showSaveFilePicker({suggestedName})`: the **user chooses the folder** (e.g. inside a synced library).
- **Overwrite:** if the user picks an existing file name, the OS dialog asks first. The app adds its own confirmation when the chosen name matches a previous export of a different project.
- **No background upload:** the app writes once, at the user's click. Sync to M365 is done by the OneDrive client, outside the app.
- **Version and checksum:** file names carry the export version (`<project>-report-v<exportSeq>-<yyyymmdd>.html`); the manifest carries checksums. The `ExportRecord` notes `destination: "save-picker"` with no path.
- **Fallback:** if the API is unavailable, use V1 download.

### V3: direct Graph write (requires approvals)

- **Destination picker:** the Microsoft picker in folder-selection mode. **No hard-coded drive, site or folder.**
- **Write:** upload to the selected folder with `@microsoft.graph.conflictBehavior=fail` by default. On conflict, show "A file with this name exists (modified by X on date). Keep both (rename) / Replace (type REPLACE) / Cancel". Replace uses `If-Match: <eTag>` so a concurrent change isn't overwritten silently.
- **Confirmation before write:** a summary of destination path, file names, size, and the boundary notice.
- **Audit:** the `ExportRecord` stores `driveId`, `itemId`, `webUrl`, `eTag`, time and user principal name (if consented). There's a local log only, because there's no app server.
- **Revocable access:** **Disconnect Microsoft account** clears the MSAL cache. Admin and user consent can be revoked in Entra / My Apps.
- **Rollback and recovery:** the app never deletes remote files. Recovery uses SharePoint/OneDrive version history and the recycle bin, linked from the conflict and success messages.

## 4. What each level changes about the data boundary

| Level | Device → M365 | M365 → device | Who moves the data |
|---|---|---|---|
| V1 | Only when the user saves a downloaded file into a synced folder | Only files the user picks | User plus OneDrive sync client |
| V2 | Same, with the destination chosen inside the app | Only the linked folder, only on Refresh | User plus OneDrive sync client |
| V3 | App writes to the user-picked folder via Graph | App reads user-picked items via Graph | App, under delegated permissions |

## 5. V3 prerequisites (all must be recorded as met before any Graph code is written)

| # | Prerequisite | Owner | Recorded value |
|---|---|---|---|
| P1 | Entra ID **app registration** (single-tenant, SPA platform) | Tenant admin | _not yet_ |
| P2 | **Redirect URI** = production origin (GitHub Pages URL or corporate static host). `127.0.0.1` for dev only if policy permits | Tenant admin | _not yet_ |
| P3 | **Delegated permissions** list and justification (least privilege), e.g. picker-plus-selected-items read; write only if V3 output is approved | Tenant admin plus owner | _not yet_ |
| P4 | **Consent model:** user consent allowed, or **admin consent** required | Tenant admin | _not yet_ |
| P5 | Conditional Access / device compliance impact on SPA token issuance | Tenant admin | _not yet_ |
| P6 | Hosting origin approved by IT/security (the code is served from a third-party static host) | IT security | _not yet_ |
| P7 | Data classification: which projects may be stored in the browser and in M365 | Information governance | _not yet_ |
| P8 | Support owner for the registration (secret-less SPA, but redirect and consent maintenance) | Owner | _not yet_ |

No V3 work starts while any row says _not yet_.

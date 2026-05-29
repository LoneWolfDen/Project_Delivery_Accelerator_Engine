# Manual End-to-End Test Script

> Execute sequentially. Each step depends on the previous.

---

## Setup

| Step | Action | Expected Result |
|------|--------|-----------------|
| 0.1 | Start application (single container) | Server running, DB initialised, health check returns 200 |
| 0.2 | Create a new Project | Project created with `status: active`, ID returned |

---

## Happy Path

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Ingest a document into the project | Artifact stored, intelligence processed, Version 1 created with `status: draft`, `version_number: 1` |
| 2 | Create Review A on Version 1 | Review A created with `status: pending`. `version.active_review_id` = Review A (auto-assigned) |
| 3 | Create Review B on Version 1 | Review B created. Active review remains Review A (unchanged) |
| 4 | Add feedback F1 to Review A | Feedback stored: `{ review_id: A, content: F1, resolved: false }` |
| 5 | Add feedback F2 to Review A | Feedback stored: `{ review_id: A, content: F2, resolved: false }` |
| 6 | Switch active review to Review B | `version.active_review_id` = Review B. Review A unchanged. |
| 7 | Add feedback F3 to Review B | Feedback stored: `{ review_id: B, content: F3 }` |
| 8 | Create Review C on Version 1 | Review C created. `injected_feedback` = [F3] (from active Review B only, NOT F1/F2) |
| 9 | Switch active review to Review C | `version.active_review_id` = Review C |
| 10 | Generate Proposal (v1) | Proposal created: `{ proposal_version: 1, status: draft, review_id: C }`. Injected feedback from Review C snapshot. |
| 11 | Submit Proposal v1 | `proposal.status: submitted` |
| 12 | Reject Proposal v1 | `proposal.status: rejected` |
| 13 | Add feedback F4 to Review C | Feedback stored on Review C |
| 14 | Create Review D | Review D created. `injected_feedback` = [F4 + any prior feedback on Review C] |
| 15 | Switch active to Review D | `version.active_review_id` = Review D |
| 16 | Generate Proposal (v2) | Proposal v2 created: `{ proposal_version: 2, status: draft, review_id: D }`. Proposal v1 stays `rejected`. |
| 17 | Submit Proposal v2 | `proposal.status: submitted` |
| 18 | Accept Proposal v2 | `proposal.status: accepted` |
| 19 | Finalise Version 1 | `version.status: finalised`. All reviews → `closed`. `finalised_at` set. |
| 20 | Trigger backward transition | New Version 2 created: `{ status: draft, version_number: 2, source_version_id: V1 }`. Version 1 unchanged. |

---

## Auto-Supersede Check

| Step | Action | Expected Result |
|------|--------|-----------------|
| 21 | On Version 2: create Review E (auto-active) | Review E active on Version 2 |
| 22 | Generate Proposal (v1) on Version 2 | Proposal v1 created as `draft` |
| 23 | Generate another Proposal on Version 2 | Proposal v1 → `superseded`. Proposal v2 created as `draft`. |

---

## Soft Warning Finalisation

| Step | Action | Expected Result |
|------|--------|-----------------|
| 24 | Add unresolved feedback to Review E | Feedback stored, `resolved: false` |
| 25 | Submit + Accept Proposal v2 on Version 2 | `proposal.status: accepted` |
| 26 | Attempt finalise WITHOUT confirm | Returns warning: "1 feedback item unresolved". No state change. |
| 27 | Finalise WITH `confirm: true` | Version 2 finalised. Unresolved feedback persists as-is. |

---

## Negative Checks (Run After Happy Path)

| Step | Action | Expected Result |
|------|--------|-----------------|
| N1 | Create review on finalised Version 1 | FAIL: 409 "Cannot add reviews to finalised version" |
| N2 | Generate proposal on finalised Version 1 | FAIL: 409 "Cannot create proposals on finalised version" |
| N3 | Edit content on finalised Version 1 | FAIL: 409 "Version is finalised" |
| N4 | Add feedback to closed Review A | SUCCESS (audit log). `added_after_close: true` |
| N5 | Create proposal with no active review (delete all reviews first on a test version) | FAIL: 400 "No active review set" |
| N6 | Set active review to review from different version | FAIL: 400 "Review does not belong to this version" |
| N7 | Skip phase: attempt `draft` → `finalised` directly | FAIL: 400 "Invalid transition" |
| N8 | Create version with empty title | FAIL: 400 "Title is required" |
| N9 | Create feedback with empty content | FAIL: 400 "Feedback content is required" |
| N10 | Finalise version with no accepted proposal | FAIL: 400 "No accepted proposal exists" |

---

## Data Integrity Spot Checks

| Step | Action | Expected Result |
|------|--------|-----------------|
| D1 | Query Version 1 proposals | Returns v1 (rejected) + v2 (accepted). Both have correct `review_id` snapshots. |
| D2 | Query Review C `injected_feedback` | Contains [F3] only. Does NOT contain F4 (added after Review C creation). |
| D3 | Query Review D `injected_feedback` | Contains Review C's feedback at time of D's creation. |
| D4 | Query superseded proposal on Version 2 | Returns full data with `status: superseded`, `superseded_at` set. Immutable. |
| D5 | Query Version 2 `source_version_id` | Points to Version 1's ID. |
| D6 | Verify version numbers | Version 1 = 1, Version 2 = 2. No gaps, no duplicates within project. |

---

## Total: 27 happy path steps + 10 negative checks + 6 integrity checks = 43 test points

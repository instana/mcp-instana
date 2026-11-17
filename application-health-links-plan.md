# Application Health: Reduce Link-Building API Calls (Skill-Only)

## Top-Level Overview

**Goal:** Cut the API calls the `application-health` skill makes to build application links, without changing any server code.

**Today:** The skill makes 5 data calls, then up to 3 `get_applications` lookups (call 6, one per linked application). That is up to 8 calls in 2 rounds.

**Target:** The skill makes 5 data calls, then exactly 1 `get_applications` lookup. That is 6 calls in 2 rounds, or 5 calls if no application is rated.

**Approach (decided with the user):**
- Calls 1-5 already return some application IDs. Reuse them instead of looking them up again.
  - Events: `entity.applicationId` with `entity.label` (the application name).
  - SLOs: `entity.applicationId`. The SLO result has no name.
  - Synthetics: `applicationIds` and `applicationLabels`, or the singular `applicationId` and `applicationLabel`.
- Run one `get_applications` call (call 6) with a `name_filter`. It supplies the `<base>` host from `_links.self`. It also supplies the ID of the application it was filtered on.
- Link an application when its ID is known. Otherwise show the name as plain text.

**Non-goals (explicitly out of scope):**
- No server or tool changes. Merging the events calls and adding `applicationId` to grouped metrics (options B and C) are not part of this plan.
- No change to classification thresholds, the verdict, or the report sections.
- No unfiltered `get_applications` call. It returns at most 50 of 80 applications, and the router can't page it.

**Evidence from the live preview tenant:**
- `application.name` is the only application tag in the GROUPING tag catalog. There is no application ID tag.
- Unfiltered `get_applications` returned 50 of `totalHits` 80, about 28 KB.
- `get_events` (`entity_type` `APPLICATION`) returned `entity.applicationId` on 2 of 3 events. It was missing on one.
- `get_test_summary_list` returned `applicationIds` and `applicationLabels` arrays.
- SLO `get_all` returned `entity.applicationId` and no name.

**Known trade-offs to keep visible:**
- Link coverage is partial by design. Events are capped at 15 per call, synthetics are paged at 20, and not every application has an event, a test or an SLO.
- SLO IDs are only useful for linking if the ID is also in the map from events, synthetics or call 6. Otherwise the SLO row shows the ID, as it does today.
- Synthetic `applicationIds[i]` and `applicationLabels[i]` appeared index-aligned in one sample. This has not been verified on more data.
- The source SKILL.md has uncommitted changes on branch `app-health-skill`. Build on top of them.

---

## Sub-Task 1: Rewrite call 6 and the Links section in SKILL.md

**Status:** `[x] done`

**Intent:** Replace the per-application lookup (up to 3 calls) with a single lookup. Add rules for building an ID-to-name map from the data already fetched.

**Expected Outcomes:**
- The skill describes exactly one `get_applications` call after calls 1-5.
- The skill describes how to build the ID map from calls 2-5, and how to pick the one name that call 6 looks up.
- The Links section says "link when the ID is known, otherwise plain text".
- The `Never guess a base or id` and `if call 6 fails, omit links` guardrails stay.

**Todo List:**
1. Edit the "Calls" step 6 (SKILL.md lines 49-53):
   - Change "at most 3" to "exactly 1".
   - Choose the lookup name in this order: worst Needs attention application with no known ID, else worst Needs attention, else worst Elevated, else busiest rated application.
   - Keep `name_filter` set to the exact application name, and keep matching `label` exactly.
   - Say that this call is the only source of `<base>`.
   - Skip call 6 when no application is rated. No call means no links.
2. Add a short "ID map" rule, placed before or inside step 6 and kept compact:
   - Build the map from calls 2-5 only: event `entity.label` to `entity.applicationId` (APPLICATION events only), and synthetic `applicationLabels` to `applicationIds`.
   - Match by exact name. Ignore entries with no ID.
   - Add the call 6 result to the map.
3. Update the "Links" section (lines 84-87):
   - Link the application name in the Needs attention table when the map has its ID.
   - Link the SLO's `entity.applicationId` as `<id>` as today. Use the map to also show the application name when the ID is in the map.
   - If call 6 fails, omit all links, because `<base>` is unknown.
4. Update the Report instructions (lines 77 and 79) so wording matches "link when the ID is known".
5. Bump the frontmatter `version` from 1.2.0 to 1.3.0. Keep the description unchanged.
6. Keep the file within the 6000-character cap enforced by `MAX_SKILL_CHARS`. Trim wording if needed rather than raising the cap.

**Relevant Context:**
- [`src/skills/application-health/SKILL.md`](src/skills/application-health/SKILL.md): lines 15 (batch description), 49-53 (call 6), 55 (forbidden calls), 77 and 79 (report), 84-87 (links).
- Line 55 forbids unfiltered `get_applications`. Keep it.
- `_links.self` format seen live: `https://<host>/api/application-monitoring/applications;id=<id>?to=...&windowSize=...`. `<base>` is everything before `/api/`.

---

## Sub-Task 2: Update the unit tests

**Status:** `[x] done`

**Intent:** Keep the tests in step with the new link behavior, and add checks that guard against going back to many lookups.

**Expected Outcomes:**
- Tests assert the single-lookup wording and the ID-reuse rules.
- Obsolete assertions are removed or changed.
- The whole `tests/skills/test_application_health_skill.py` suite passes.

**Todo List:**
1. In `TestSkillLinks` and `test_links_call_is_after_synthetics_call`, review the asserted strings: `"6. Links, after 1-5"`, `"`_links.self` in a call 6 result"`, `"without `name_filter`"`. Update any that changed in sub-task 1.
2. Add assertions that:
   - the skill states a single lookup ("exactly 1" or equivalent), and no longer says "at most 3";
   - the skill mentions reusing IDs from events (`entity.applicationId`), SLOs and synthetics (`applicationIds`);
   - links are skipped when the ID is unknown ("plain text" or equivalent).
3. Keep the existing assertions for `_links.self`, the link format, and `Never guess a base or id`.
4. Keep `test_lightweight` (6000-character cap) as is.
5. Run `pytest tests/skills/test_application_health_skill.py`.

**Relevant Context:**
- [`tests/skills/test_application_health_skill.py`](tests/skills/test_application_health_skill.py): `TestSkillLinks` (line 141), `test_links_call_is_after_synthetics_call` (line 135), `MAX_SKILL_CHARS` (line 30).

---

## Sub-Task 3: Regenerate the content hash and validate

**Status:** `[x] done`

**Intent:** The skill file changed, so its `content_hash` frontmatter field is stale. The skill validator checks it.

**Expected Outcomes:**
- `content_hash` in the frontmatter matches the new file contents.
- The skills validator reports no errors or new warnings.

**Todo List:**
1. Run `python src/skills/validate_skills.py --fix` from `mcp-instana`.
2. Re-run the validator without `--fix` and confirm it is clean.
3. Re-run the sub-task 2 tests, since the hash is part of the file.

**Relevant Context:**
- [`src/skills/validate_skills.py`](src/skills/validate_skills.py): the `--fix` option and the `content_hash` check around lines 252-276.
- [`src/skills/skill_files.py`](src/skills/skill_files.py): `compute_content_hash`.

---

## Sub-Task 4: Live verification and benchmark check

**Status:** `[ ] pending`

**Intent:** Confirm on a real tenant that the new flow produces the same report with fewer calls, and that the assumptions hold.

**Expected Outcomes:**
- A run of the skill on the preview tenant makes exactly 5 calls in round 1 and exactly 1 call in round 2.
- Links in the report resolve correctly: the host matches the tenant, and the app IDs match the right applications.
- The unverified assumptions are checked and recorded in this plan.

**Todo List:**
1. Run the skill on a health query, for example "Are all my applications healthy?", and count the tool calls.
2. Spot-check every link:
   - the host in `<base>` matches the tenant;
   - the `appId` belongs to the application whose name is linked.
3. Check that synthetic `applicationIds[i]` matches `applicationLabels[i]` on a test with 2 or more applications. For example, `TestRAG2` has `["test","markb"]` and `["AxnuHKeESNiHN8meGulC4w","yoA_pO9fTeesYbs2WfTTNg"]`. If the arrays are not index-aligned, drop synthetics as an ID source and note it here.
4. Check that events missing `entity.applicationId` are skipped cleanly. One of the 3 sample events had no ID.
5. Run the existing benchmark queries for application health (`ibm-internal-only/tools/benchmark_config.yaml`, queries around lines 116-125) and compare tool-call counts and token usage before and after.
6. Record findings and any plan adjustments in a short "Results" note appended to this file.

**Relevant Context:**
- [`ibm-internal-only/tools/benchmark_config.yaml`](ibm-internal-only/tools/benchmark_config.yaml): application-health prompts.
- Preview tenant used for analysis: `preview-instana.instana.rocks`.

---

## Rollout Notes
- Do the sub-tasks in order, one at a time. Each is reviewable on its own.
- If sub-task 4 shows link coverage is too thin for Needs attention applications, the follow-ups are server-side (merge events calls, add `applicationId` to grouped metrics, return `base_url` from the skill tool). They are out of scope here.

## Progress Notes
- Sub-tasks 1-3 done. SKILL.md is 1.3.0 and 5,964 chars (cap 6,000). The `content_hash` was regenerated and the validator reports 0 failures and 0 warnings.
- Tests: `.venv/bin/python -m pytest tests/skills/` gives 313 passed. Use the project `.venv`, because system Python lacks `fastmcp`.
- A pre-existing ruff E741 in `tests/skills/test_instana_genai_instrumentation_skill.py:424` is unrelated and was left alone.
- Sub-task 4 (live verification and benchmark) is still pending.

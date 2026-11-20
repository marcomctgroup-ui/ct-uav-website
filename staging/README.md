> **Historical log only - 20 November 2026:** The instructions below describe earlier workspace states. They are not current operating instructions. The current published build is connected and enabled on the existing staging service. Read the dated root [technical guide](../README.md) for current setup, endpoints, credentials and release limits.

> **Repository note (17 November 2026):** this log was copied from the CT UAV Marcom workspace. Paths such as `projects/main-website/staging/` and links to `HANDOFF.md` or `handoff/` refer to that workspace. In this repository, run the same commands from the root with `staging/` (for example `python staging/build.py`). See the root `README.md`.

# CMS tools update - 17 November 2026

New: `cms_refresh_guard.py` (editor-safe refresh; required by both refresh CLIs), `cms_delivery.py` (CDN snapshot read, token redacted), `cms_published_build.py` (published-only generation, fail closed, keeps last good output; not connected to build.py), `cms_preview_build.py` (draft preview into `dist/cms-preview/` only when `STORYBLOK_PREVIEW_TOKEN` exists at build time), `cms_preview.js` (worker gate for `/cms-preview/*`: Storyblok signed link then session cookie; preview CSP), `cms_bridge.js` (Visual Editor live text). Tests: `python cms_refresh_guard_test.py`, `cms_delivery_test.py`, `cms_published_build_test.py`, `cms_preview_build_test.py`; `node cms_preview_test.mjs`. Details: handoff/20261116-storyblok-resume-work-record-v01.md.

# CMS local candidate - 13 November 2026

Selected candidate: refactor-v12, based on v11. The public builder now bundles a published-only CMS reader. It does not import the separate draft generator. Install the pinned optional dependency with `python -m pip install -r projects/main-website/staging/cms-requirements.txt` before local draft generation. The ordinary public build does not need it.

The DECARB 22 browser script requests `/api/cms/decarb22`. `cms_published.js` reads only the original published pilot and returns only six display fields. It requires encrypted `STORYBLOK_PUBLIC_TOKEN`; it does not use the legacy token setting or accept draft queries. `cms_worker.js` forwards the existing voice endpoint unchanged. Missing voice bindings still return 503. No voice service is activated.

Cloudflare also stores a separate encrypted `STORYBLOK_PREVIEW_TOKEN`. It is not bundled into browser code. The exposed historical Preview key needs revocation after the replacement passes hosted checks. No key values belong in project records.

- `cms_refresh.py`: prepare source-based draft additions from a complete Management API export. It does not write to Storyblok.
- `cms_site.py`: render the four representative records into the existing v11 multi-file layouts. It validates explicit bilingual fields and rejects unsupported mappings. Output must stay below ignored staging/checks.
- `cms_fields.js`: apply CMS-owned field translations without legacy dictionary replacement.
- `cms_serve.py`: serve only generated output on 127.0.0.1 (default port8793), with a128-request queue, noindex and no-store. This is local HTTP review, not a hosted protected preview.
- `cms_preview_auth.js`: server-side Storyblok signed-preview validation. The private credential is configured, but this module is not connected to a public preview endpoint. It does not require Cloudflare Zero Trust.
- Tests: `python projects/main-website/staging/cms_site_test.py`; `python projects/main-website/staging/cms_generate_test.py`; `node projects/main-website/staging/cms_preview_auth_test.mjs`.
- Published reader tests: `node projects/main-website/staging/cms_published_test.mjs`. Local Wrangler 4.158.0 compiled the bundled worker with compatibility date 2026-11-04. Without credentials, CMS and voice endpoints returned 503; a product route returned 200. Hosted API validation remains pending.

Read the root handoff and the 13 November CMS work record for exact record IDs, checks and remaining work. Do not publish these draft snapshots, select generated output for staging or enable a webhook from these commands alone.

# GitHub organization move — 11 November 2026, v01

The repository moved from `privatekal/ct-uav` to the company organization
repository `marcomctgroup-ui/ct-uav`. Cloudflare Pages was reconnected to the
organization repository on branch `staging`; the staging site answered HTTP
200 at the unchanged URL https://ct-uav-staging.pages.dev/ after the move.
The `privatekal/ct-uav` reference below is historical only.

# Current revision: v08 r02 - 9 November 2026

Selected source: refactor-v08. The static multi-file site retains deferred video and 3D loading. The build also emits a Cloudflare Pages advanced-mode worker and _routes.json. Only /api/transcribe invokes the worker. Internal readable sources, checks and supplied originals are excluded.

Voice activation is pending: encrypted OPENAI_API_KEY secret and D1 binding VOICE_DB in the company Cloudflare project. The CLI is not authenticated in this session. The endpoint fails closed with 503 if either binding is absent. See ../refactor-v08/README.md for flow, source records and limits. No live speech or production D1 check is claimed.

Local worker checks used Wrangler 4.158.0 / compatibility date 2026-11-04. The actual local worker compiled, returned 503 without the key, and admitted six concurrent invalid-content test requests before returning 429 to two more. These tests did not send audio to OpenAI. The Python static test server now uses a 128-request queue to avoid local connection refusals under multi-frame checks. It remains a hosting approximation.

Full standard guardrails: 0 FAIL / 0 WARN across seven routes at five widths. Guardian round 2: PASS, 0 FAIL / 3 WARN; final records completed after review. Fresh Lighthouse 13.6.0 mobile local: Performance 74 / Accessibility 100 / Best Practices 100; non-video 1,565,788 B, video 1,400,112 B, no run warnings. See root HANDOFF.md for the commit and hosted deployment result. The older dated setup record follows.

# CT UAV automatic staging

9 November 2026, v02. Automatic update verified. Selected source: refactor-v07 r03.

Staging URL: https://ct-uav-staging.pages.dev/
Company Cloudflare account: `marcom.ctgroup@gmail.com`.
GitHub source: `privatekal/ct-uav`, branch `staging`.

This folder prepares the existing multi-file website for Cloudflare Pages.
The build keeps the selected website source unchanged. It does not create a ZIP.

Run from the repository root:

    python projects/main-website/staging/build.py

Cloudflare Pages settings:

- Framework: None.
- Build command: `python projects/main-website/staging/build.py`.
- Build output: `projects/main-website/staging/dist`.
- Root directory: repository root.
- Deployment branch: `staging`. Automatic deployments enabled.
- Other preview branches: disabled. This project is for the staging branch only.
- Build watch paths: website refactor versions, staging tools, and `.gitattributes`.
  Unrelated reports do not trigger a website deployment.
  Exact include patterns: `projects/main-website/refactor-*`,
  `projects/main-website/staging/*`, `.gitattributes`. Cloudflare's trailing `*`
  includes nested paths. Do not replace these with shell-style `**` patterns.

The output contains the entry shell, route entries, page documents and separate
assets. It excludes source records, historical versions, checks, source-code and
README files. Do not use the workspace root or the complete refactor folder as
the public output.

The generated header file retains the selected source's security headers,
staging noindex header and cache policies. A generated `robots.txt` disallows
indexing for this staging project. The build groups only immutable asset
prefix or suffix patterns whose files all have verified content hashes. It checks equivalent
cache coverage for every asset and enforces Cloudflare's 100-rule, 2,000-character
line and 25 MiB per-file limits. Original asset bytes and CRLF are preserved.
The build stops if Git LFS pointers appear instead of downloaded media. Fifteen
current model/video files use LFS. All fifteen deployed media files passed the
first full browser byte check. Repeat media checks when media files change.

`dist/` and `checks/` are generated local output and are not committed. Rebuilding
replaces only the fixed `staging/dist/` folder. The manifest records copied paths,
sizes and SHA-256 hashes in `checks/build-manifest.json`.

Future revisions: edit and verify the selected website, update `config.json` if
the selected version changes, then commit and push the revision to the connected
staging branch. Cloudflare builds and updates the same staging URL. Public release
and the stopped chatbot service are outside this setup.

Local header and extensionless-URL review:

    python projects/main-website/staging/serve.py

This serves `http://127.0.0.1:8788/`. It is a local approximation, not a Cloudflare
runtime. The first deployment's 770 source files, hashes, headers and redirects
passed a same-origin check in the shared browser. CT-FRYAN's 3D stage rendered.
That check also confirms that all 15 LFS media files arrived with their full bytes.
Plain Python HTTP requests received Cloudflare 1010/403; no Cloudflare protection
was disabled. Browser requests and the Edge Lighthouse run succeeded.

Local full guardrails: 0 FAIL / 0 WARN. Guardian review: 0 FAIL / 1 WARN about
local server emulation. Actual deployed-file browser checks: 770 checked, no
differences. One Lighthouse 13.6.0 mobile laboratory run against the first hosted
revision: Performance 84, Accessibility 100, Best Practices 100; non-video
1,520,750 B, video 1,400,262 B, no run warnings. SEO 58 reflected noindex and the
missing robots file. The generated robots file is now deployed and checked.
Do not treat the local and hosted scores as a controlled speed comparison.

Automatic update proof: GitHub push `49063ba` triggered deployment `4ccae6e5`
without a manual retry. The Cloudflare dashboard reports success and 2m 1s.
The same staging URL serves exactly `User-agent: *\nDisallow: /\n` as text/plain.
The root, CT-FRYAN page and model still match their local hashes and expected
headers. Local evidence: `checks/automatic-update-check.json`.
The earlier `a386008` update was skipped under the first watch patterns.
The corrected single-star patterns above passed the automatic update test.

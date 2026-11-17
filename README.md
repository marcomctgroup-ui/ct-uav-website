# CT UAV main website

Source code for the new CT UAV main website (staging version). CT UAV is a member of CT Group.

- Staging preview: https://ct-uav-staging.pages.dev/ (noindex, not public)
- Public company website (not built from this repository): https://ctuav.global

## Important: where the staging site builds from

This repository is a clean copy of the website from the Marcom workspace repository (`marcomctgroup-ui/ct-uav`, branch `staging`, commit `d10783f`, 17 November 2026).

**The Cloudflare Pages staging project still builds from the Marcom workspace repository, not from this repository.** A push to this repository does not change the staging site. Until the team agrees which repository is the master copy, coordinate changes with the CT UAV Marcom team so the two copies do not diverge.

## Repository layout

| Path | Content |
| --- | --- |
| `refactor-v15/` | Current website source: `index.html`, route folders, `pages/`, `assets/`, `_headers`. `source-code/` and `source-inputs/` hold readable sources and input records; the build does not publish them. |
| `staging/` | Build script for Cloudflare Pages, Storyblok CMS scripts, Cloudflare worker code and their tests. `staging/README.md` is the change log copied from the Marcom workspace. |
| `staging/config.json` | Selects the website source folder (`refactor-v15`). |
| `handoff/` | Storyblok record snapshots (JSON). The CMS tests read them. They contain no keys. |
| `QUALITY-GUARDRAILS.md` | Design and quality rules for the website. Read before you change a website file. |
| `quality-guardrails.json` | Measured limits for the guardrail checker. |
| `checks/build-tools/20261022-ctuav-main-website-guardrails-check-v01.py` | Guardrail checker (Playwright). |
| `.claude/agents/main-website-guardian.md` | Review agent definition for Claude Code. |

## Build

Requires Python 3.10 or later. No package is necessary for the public build.

```bash
python staging/build.py
```

Output: `staging/dist/` (ignored by Git). The build copies only public files, generates `_headers`, `_routes.json`, `_worker.js` and `robots.txt`, and keeps the staging `noindex` rule.

Cloudflare Pages settings, if this repository is connected later:

- Framework: None
- Build command: `python staging/build.py`
- Build output: `staging/dist`
- Root directory: repository root

Serve the output locally:

```bash
python -m http.server 8799 --bind 127.0.0.1 -d staging/dist
```

## Media files (Git LFS)

The 3D models and videos in `refactor-v15/assets/` use Git LFS (see `.gitattributes`). Install Git LFS before you clone. Without Git LFS, these files download as small text pointers and the build stops.

## CMS (Storyblok)

The DECARB 22 page reads published content through `/api/cms/decarb22` (`staging/cms_published.js`). The static page copy is the fallback when the CMS is not available.

Keys are Cloudflare encrypted secrets only (`STORYBLOK_PUBLIC_TOKEN`, `STORYBLOK_PREVIEW_TOKEN`). Never add a key to this repository. The tokens in the test files are fake test values.

Optional draft tools need extra packages:

```bash
python -m pip install -r staging/cms-requirements.txt
```

## Tests

From `staging/`:

```bash
python cms_site_test.py
python cms_refresh_guard_test.py
python cms_delivery_test.py
python cms_published_build_test.py
python cms_preview_build_test.py
node cms_preview_auth_test.mjs
node cms_preview_test.mjs
node cms_published_test.mjs
node voice-worker.test.mjs
```

`cms_site_test.py` needs the packages in `staging/cms-requirements.txt`. On 17 November 2026 all of these tests passed in this repository layout. `cms_generate_test.py` and `cms_generate.py` need the older `refactor-v09` templates, which are not in this repository.

## Quality checks

1. Read `QUALITY-GUARDRAILS.md`.
2. Install Playwright for Python (`pip install playwright`, then `playwright install chromium`).
3. Run the checker on the changed HTML files:

```bash
python checks/build-tools/20261022-ctuav-main-website-guardrails-check-v01.py <changed .html files>
```

Fix every FAIL. Fix or explain every WARN. The checker opens files with `file://`, so pages that fetch `/api/...` report a script error in that mode. Check those pages through an HTTP server as well.

## Known open items

- The CT Ency assistant script (`assets/js/ctencyscript-*.js`) still points to `../../main-website-glass-3d-v04.html`, a file from an older demo. The same link exists on the current staging site. The CT Ency service is stopped.
- Voice transcription (`/api/transcribe`) needs Cloudflare secrets and a D1 binding. It returns 503 until they exist.
- Product data must match approved CT UAV sources. Do not add or change specifications without CT UAV confirmation.

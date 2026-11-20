# CT UAV website - DAIT technical handoff

20 November 2026 - v01 - Website source: refactor-v18

CT UAV - Member of CT Group Hi-tech.

This is the website-only handoff repository. It is public. Keep credentials,
internal Marcom reports, private screenshots and unrelated project files out.

- Staging: https://ct-uav-staging.pages.dev/ (publicly accessible review site, noindex).
- Official domain: https://ctuav.global (DAIT controls its hosting and release).
- Current Cloudflare staging still builds from the Marcom repository, branch `staging`.
  This repository is NOT connected to that deployment. A push here does not update it.
- This revision updates the old v15 handoff copy to v18. Previous source is recoverable
  from Git history. No production release, domain change or CMS migration beyond the
  four product pages is included.

## 1. Architecture and source

The site uses separate HTML route shells, iframe page documents, CSS, JavaScript,
Montserrat fonts, images, video and GLB models. Media stays separate from HTML.

| Path | Purpose |
| --- | --- |
| `refactor-v18/index.html` | Home shell |
| `refactor-v18/products/`, `applications/` and other route folders | Direct-entry route shells |
| `refactor-v18/pages/` | Separate page documents |
| `refactor-v18/assets/` | Website media, fonts, styles and scripts |
| `refactor-v18/source-code/` | Readable website sources, URL settings and selected maintenance tools; not hosted |
| `staging/` | Build, CMS renderer, worker, local server and tests |
| `staging/config.json` | Selects `refactor-v18` |
| `handoff/` | Website test fixtures; historical test inputs, not current content approval |
| `checks/` | Quality checker; not hosted |

The transfer copies website asset/page bytes. Legacy preview test paths are adapted
for the root layout and selected v18 source. Do not run historical revision builders.

## 2. Install and build

Use Python 3.10 or later, Node.js for worker tests, and Git LFS for media.
Download real LFS media for the selected source; unresolved pointer files stop the build.

```bash
git lfs install
git lfs pull
python -m pip install -r staging/cms-requirements.txt
python staging/build.py
python staging/serve.py --port 8799
```

Open http://127.0.0.1:8799/. The local server is a static hosting approximation.
Cloudflare worker endpoints do not run there. The old pilot API can therefore
return 404 locally while its static fallback remains available.

Output is `staging/dist/`. It is generated, ignored and replaced by each build.
The build uses a public-file allowlist, rejects unresolved LFS pointers and oversized
files, checks copied hashes and validates cache/header limits. Readable sources,
fixtures, test records and the private visual guide are excluded from hosting.

## 3. Static and published CMS modes

| Build setting | Result |
| --- | --- |
| `STORYBLOK_PUBLISHED_BUILD=0`, or absent | Static source; works without CMS credentials |
| `STORYBLOK_PUBLISHED_BUILD=1` | Published Storyblok content replaces mapped fields in four product templates |

Current company staging uses mode `1`. The four products are DECARB 22, DECARB 54,
CT-CROVA 254 and CT-PEGAS 230, plus their shared cards. Four products and 16 referenced
asset/technology records were published with Haykal's authorization on 20 November.
Other pages remain template-owned. This is not full-site CMS coverage.

In enabled mode the build reads published records only. Required products and used
assets/technologies must be reviewed, ready in EN/VI and published. Missing or invalid
content stops the build. There is no silent static fallback in this mode; a failed
Cloudflare build leaves the last successful deployment live.

## 4. Editing, preview and publication

1. Edit the mapped Storyblok field and its English/Vietnamese text.
2. Save the draft. Save does not publish the change.
3. Use the protected Visual Editor preview. Some text updates live; specification,
   chapter and other derived fields require a build.
4. Review content, product identity and media. Set readiness only after review.
5. Publish the approved product and required referenced content.
6. The existing Storyblok Publish hook starts the current Cloudflare staging build.
7. Confirm the deployment result, page content, language and media on staging.

Before moving hosting or repository connections, DAIT must confirm and reconnect the
hook to the chosen build target. Do not duplicate a build already started by the hook.
The hook URL is a secret; it is not included here.

## 5. Environment and worker endpoints - names only

| Name | Purpose |
| --- | --- |
| `STORYBLOK_PUBLIC_TOKEN` | Published-content delivery; encrypted secret |
| `STORYBLOK_PREVIEW_TOKEN` | Draft preview and signed editor access; encrypted secret |
| `STORYBLOK_SPACE_ID` | Company CMS space identifier |
| `STORYBLOK_PUBLISHED_BUILD` | Public-build mode, `0` or `1` |
| `ASSETS` | Cloudflare's automatic static asset binding |

Never commit real credentials or place them in public files, screenshots, URLs or
reports. Transfer access privately through company-controlled accounts. Do not send
masked empty secret values from an API read back in an update; use the dashboard
when an API update cannot safely preserve existing secrets.

- `/api/cms/decarb22`: existing published-only six-field pilot endpoint.
- `/cms-preview` and `/cms-preview/*`: protected draft preview; unauthenticated access returns 401.
- `/api/transcribe`: retained voice endpoint. The chatbot service is stopped; no voice
  activation is included. It needs separate secrets/bindings before use.
- All normal website routes serve static files generated by the build.

Private draft preview has separate framing/CSP rules. Keep it protected after a move.
Review CSP, worker restrictions, media origins and any new analytics/form services
before changing hosting. Existing cloud account ownership/access must be confirmed.

## 6. Hosting settings and production work

Current staging uses Cloudflare Pages, framework None, build `python staging/build.py`
when this root layout is connected, output `staging/dist`. These are handoff settings,
not a request to reconnect the current site. The existing Marcom deployment uses its
workspace-relative build command instead.

The build is deliberately a STAGING build: it writes robots exclusion and retains
noindex headers. Do not deploy this output to production unchanged.

DAIT must decide hosting and the build/repository connection, then configure the
official domain, DNS and SSL. Keep staging excluded from indexing. On the approved
production release, use reviewed production robots, sitemap and indexing headers.

## 7. URLs, SEO and old content

Current route paths are provisional. Maintain route and canonical settings centrally
in `refactor-v18/source-code/20261117-v16-seo-config-v01.json` and its URL map.
Do not manually edit each page for a URL change. The selected maintenance script is
provided as source; test a copy and inspect its complete diff before regeneration,
so later v18 loading/content fixes are preserved.

The site has per-route titles, descriptions, canonical tags, structured data, a sitemap
and a 404 page. EN/VI currently share URLs. Separate Vietnamese URLs and hreflang
need DAIT's URL decision. Full document navigation currently resets English.

A dated old-site inventory and redirect draft are supplied privately with the visual
guide. The draft covers 309 addresses, including 231 old news articles as of
18 November. Targets are proposals, not approved final URLs. DAIT must select a news
retention/migration plan and test 301 redirects before replacing the old site.

## 8. Forms, privacy, analytics and ownership

The Contact form and inquiry cart currently validate fields but do not send messages.
DAIT must implement the sending backend and spam controls. Intended recipient:
info@ctuav.global. Confirm how displayed representative addresses should be used.

Management-approved privacy/consent text, any cookie controls, analytics tool/account,
Search Console ownership and sitemap submission remain release decisions. No analytics
purchase, legal wording approval or working email delivery is claimed by this handoff.

## 9. Checks and evidence

```bash
python -m unittest discover -s staging -p 'cms_*test.py'
node --test staging/cms_published_test.mjs staging/cms_preview_auth_test.mjs staging/cms_preview_test.mjs staging/voice-worker.test.mjs
```

Optional browser checks need Playwright and a supported browser. The included checker
uses Edge when available and Chromium as a fallback. Read the quality rules before
changes. Check through HTTP for route/API behavior; file URLs are not hosting proof.

Source staging evidence dated 20 November: four product routes passed EN/VI/EN,
refresh and script-error checks. Final five-route/five-width guardrails were 0 FAIL /
0 WARN after repeating one transient loading capture. Hosted Home mobile Lighthouse
13.6.0 scored 96, with 1,409,242 non-video transfer bytes. This is one laboratory run,
not a full-site PageSpeed average or final-host performance guarantee. The private
visual guide gives dates, scope and screenshots. New checkout tests are recorded there.

## 10. Known limits and recovery

- Phone mascot/title overlap remains.
- Language handler tests do not prove every phone pointer path; full navigation resets English.
- Product/template mapping covers four products, not the whole catalog.
- Contact/cart sending and privacy/analytics setup remain open.
- CT Ency remains stopped. Point 5 content-network rollout and expert articles are deferred.
- Deliberate unpublish/rollback drills and a fresh authenticated preview recheck remain open.

A failed enabled build must keep the previous live deployment. For an approved recovery,
restore the last successful deployment, correct/restore the CMS record and rebuild.
Static mode can be selected explicitly for a recorded rollback, but its content may
be older than CMS content. DAIT must assign backup, restore, monitoring and incident owners.

## 11. Release acceptance checklist

- [ ] Agree hosting, master repository and company access owners.
- [ ] Verify build and LFS media in a fresh checkout.
- [ ] Verify CMS publishing, hook target, protected preview and recovery on the chosen host.
- [ ] Agree final URLs, EN/VI URL behavior, old news treatment and redirects.
- [ ] Complete forms, consent/privacy text, analytics and Search Console.
- [ ] Check desktop/phone routes, media, language, security and final-host performance.
- [ ] Confirm backups, rollback, monitoring and support owners.
- [ ] Obtain Supervisor release approval; DAIT performs the official-domain deployment.

Marcom supplies approved copy/assets and reviews the content with Quỳnh Tiên.
Supervisor Ms. Nguyễn Tân Hoàng Phương (Fiona) gives final approval. DAIT owns the
official hosting/domain release and its technical acceptance work. No email is sent
by this handoff preparation.

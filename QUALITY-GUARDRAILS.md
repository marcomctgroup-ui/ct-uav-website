# Main website demo — quality guardrails

> **Repository note (17 November 2026):** this file was copied from the CT UAV Marcom workspace (`marcomctgroup-ui/ct-uav`, `projects/main-website/`). Paths in the rules and history below refer to that workspace. In this repository, the files are at the root: `quality-guardrails.json`, `checks/build-tools/20261022-ctuav-main-website-guardrails-check-v01.py` and `.claude/agents/main-website-guardian.md`. Components, older versions and `deliverables/` paths are not in this repository.

Version v02 r09 · 6 November 2026 · Owner: Haykal

These rules keep the main website demo consistent. Each rule comes from feedback that Haykal, Quỳnh Tiên, or the higher-ups gave more than once. Every agent must read this file **before** it changes a website file in this repository, and must run the checks **before** it reports the work as complete.

- Measured limits: [`quality-guardrails.json`](quality-guardrails.json). Change a limit only when Haykal approves it. Record the change in [Change log](#change-log).
- Automatic checker: `checks/build-tools/20261022-ctuav-main-website-guardrails-check-v01.py`
- Review agent: `.claude/agents/main-website-guardian.md` (agent name `main-website-guardian`)

## How to use these rules

1. Before you edit, read sections A to D. Find the rules that apply to the component.
2. Make the change.
3. Run the checker on the changed files:
   `python checks/build-tools/20261022-ctuav-main-website-guardrails-check-v01.py <changed .html files>`
   With no file names, the checker finds the latest version of each component and the latest combined file.
4. Fix every **FAIL**. Fix or explain every **WARN**.
5. Ask the `main-website-guardian` agent to review the change with screenshots. It checks the visual rules that a script cannot measure.
6. In the handover, give the checker result as numbers (FAIL / WARN) and list the items that stay open. Do not say "all checks passed" if a FAIL remains.

Do not lower a limit or add an exception to make a check pass. Ask Haykal first.

---

## A. Measured rules (the checker tests these)

### G1 — Text must not be small

| Item | Desktop and tablet | Phone (≤ 480 px) |
| --- | --- | --- |
| Any visible text | 14 px or more | 13 px or more |
| Text on a button or link | 14 px or more | 13 px or more |
| Primary actions (Payload options, Contact, Explore) — the guardian agent checks this row | 15 px or more | 14 px or more |

- Small labels (eyebrows, numbers "01", captions, units like "kg") are text. They follow the same limit.
- Use larger sizes for model names, figures, and headings. Do not make body text smaller to fit a layout. Change the layout.

**Why:** Haykal asked for larger text or controls in almost every round:
05 Oct (bottom navigation, About tabs, logo, form text, Back button) · 07 Oct (larger tab controls, cards, filters) · 08 Oct (Payload options) · 14 Oct (Hero buttons, arrows, pause; product navigation 16/14/13 px; Contact button 15 px) · 21 Oct (Payload options again, 62 px high with 15 px text).

### G2 — No dark colour except text

- Text, thin lines, and small icons can be dark.
- Do **not** use a dark fill for any surface: cards, buttons, dropdowns, bars, footers, dialogs, toasts, badges, or page sections.
- Do **not** put a dark shade or dark gradient over photos or video.
- Use light surfaces: white `#ffffff` and the palette soft surface `--site-soft`. Accent and hover colours come from the review palette (rule G9), not from a fixed orange.
- "Dark" means a colour with relative luminance below 0.2 (about `#7c7c7c` or darker) and opacity 35% or more.

**Why:** the higher-ups do not like dark colour. History:
05 Oct — the heavy dark overlay was removed from the hero video · 07 Oct — "No dark layer covers the video" · 09 Oct — the Supervisor accepted Orange, and the Navy prototype stopped · 14 Oct — the black Navbar dropdown (v05) went back to white (v06); the product footer bar was removed · 21 Oct — the black "All products" card changed to a light card (now the palette soft surface).

### G3 — Controls must be large and easy to see

- Buttons and links: 44 px high or more (the checker gives FAIL below 36 px and WARN below 44 px).
- Payload options: 62 px high on desktop, full width on phones. Contact buttons: 54 px or more.
- A button on a light surface must have a visible edge or fill. A white border on a light background is not visible (14 Oct Contact button problem).

### G4 — Text must be easy to read on its background

- Contrast 4.5 : 1 or more for normal text. 3 : 1 or more for large text (24 px, or 18.6 px bold).
- The checker gives FAIL below 3 : 1 and WARN below 4.5 : 1.
- Do not put white text on a palette fill (orange `#F4AE52` or blue `#a9d8e8`). Use `--site-fill-ink`.
- Do not make text light grey to make it look "quiet". Use a smaller weight or more space instead.

### G5 — Do not fade text

- Text and its parent elements must have 78% opacity or more after animations end.
- The accepted value for Hero slide copy is **80%** (07 Oct and 14 Oct). Do not go lower.

### G6 — Montserrat only

- All text uses Montserrat. The current multi-file website uses shared WOFF2 files with `font-display: swap`; bundled OTF files belong to historical demos. Do not add a second font family.

### G7 — No sideways scroll

- No horizontal page overflow at 1440, 1024, 768, 390, and 320 px.

### G8 — No broken parts

- All images load. No script errors in the console.

### G9 — Three review palettes on every page

- Every page has the same three review palettes: **Grey & white** (default, `mono`), **Orange v72** (`orange`), and **Pastel blue** (`blue`). Do not call the first option "Black & white". We avoid black.
- **Since Glass 3D v04 r07 (30 Oct, Haykal):** there is one palette, **Grey & white** (`mono`). The review colour switch is removed from the Navbar and Night mode is removed from the demo. `components/shared/night-mode-v01.css` stays in the folder as history and is not injected. The `orange` and `blue` tokens remain in the code, and the checker still measures them. A page must still take accent colours from the shared tokens, so a later palette selection needs no rework.
- Earlier state, for history: Glass 3D v04 r02 to r06 had a review switch with **Grey & white** and **Night mode** (27 Oct round 3). Haykal removed Night mode on 30 Oct (round 4).
- Review controls must not cover page content (22 Oct: a bottom-left switch covered hero buttons and a spec figure). Page-level review bars stay hidden in the combined demo.
- Components take accent colours only from the shared tokens in `components/shared/site-palette-v01.css` (`--site-accent`, `--site-accent-text`, `--site-soft`, `--site-soft-line`, `--site-fill`, `--site-fill-ink`, `--site-fill-line`), or from rules under `[data-theme="…"]`.
- Do **not** hardcode orange or blue in a component. Orange shows only when the Orange v72 option is selected.
- The checker measures each page in all three palettes, and gives WARN for a fixed palette colour in a component style file.

**Why:** 22 Oct — Haykal found orange on the Home product cards and on About, but only the product pages had the three options. The orange came from the Orange v72 sales kit rules. The sales kit uses Orange because the Supervisor accepted it for the sales kit. The main website palette is still a review choice.

---

## B. Visual rules (the guardian agent checks these with screenshots)

### V1 — Use references for layout ideas only

- DJI, EHang, XAG, and other sites are layout references. Do not copy their layout one to one. Do not copy their images, logos, text, or claims.
- 21 Oct: Haykal rejected Home products v01 because it was "100 percent plagiarizing DJI".
- When a layout changes a lot, first show 2 to 4 simple layout options (a quick sketch or wireframe). Build only the option that Haykal selects. This saves credit and time.

### V2 — UAV images

- Before each image or video addition, inspect the source and the rendered result. For video, inspect the start, middle, end, and every scene change. Remove blank end cards and frames that lose the UAV. Check the whole retained clip.
- Check UAV visibility on desktop and phones. Haykal's latest clarification (29 October): titles may overlay the UAV. Keep full-screen video and center the main UAV; edge cropping is allowed. Do not add a separate title area or small video panel. Do not let the specification strip cover the video.

- Use transparent UAV cutouts on one plain light background for all cards in a group (Home products, Navbar). Exception approved by Haykal on 22 Oct: the 16 product-line cards on the Products page use the Orange v72 sales kit card photos, because the cutout set repeats the same UAV on several lines. Do not mix cutouts and photos in one card group.
- No white box, white halo, or white gaps around the UAV: check under the wings, between skids, between landing legs, and in the tail area (21 Oct r02 and r03 were only for this problem).
- Do not change the UAV shape, logo, colour, or model name. Compare each new cutout with its source image.
- CT-FYRAN cutout: a human check against Haykal's 13 Oct image is still PENDING CONFIRMATION.

### V3 — Equal and aligned cards

- Cards on the same row and at the same level have the same size (21 Oct: CT-PEGAS 230 and CT-FRONA 44).
- UAV images in a group have a similar visual size and position.

### V4 — Less text, clean layout

- Keep UI copy short. Use white space. No decorative frames or "stage art" (13 Oct, Navbar v04 was cleaner).
- Each product card is one link to its product page. No Contact link on cards (21 Oct).
- Show a UAV selection (a list of models or lines) one time on a page. Do not repeat the same models in several sections, and do not add decorative background text or number rows (22 Oct: Products v02 "spamming UAV selection").
- Review-only controls (palette switch, review bar) are not part of the website. Remove them when Haykal selects a final option.

### V5 — Calm and stable motion

- Section reveals take about 1800 ms, and each section reveals once (14 Oct: "too fast", then repeated fading).
- Never leave content at opacity 0 after an animation (14 Oct: blank dropdown).
- Support reduced-motion settings.

### V6 — Light, modern technology look

- The site looks light and clean. The Grey & white palette means **white and light grey surfaces with dark text**, not black surfaces.

---

## C. Content rules

- Specifications, technologies, and payload concepts come from Orange v72 and approved CT UAV sources. Do not invent or average numbers. Mark draft copy as draft.
- Keep the payload compatibility note. Model compatibility is PENDING CONFIRMATION.
- Use product names exactly as approved. "CT SKYSILK" or "CT-SKYSILK" is PENDING CONFIRMATION.
- Pages that do not exist yet show the planned-page message.
- Do not put third-party images, logos, or claims into CT UAV pages.

## D. Process rules

- **"Edit the same file"**: when Haykal asks for this, change the same HTML. Save the old bytes in `deliverables/checks/history/` first. Add a revision number (r02, r03 …) in the README.
- Otherwise make a new version (`vNN`) and keep the old version.
- After each change, update the main website `README.md` and `HANDOFF.md`.
- Future website revisions keep the multi-file structure defined in [AGENTS.md](AGENTS.md). Serve `index.html`, `pages/` and separate assets through HTTP. Do not rebuild one offline HTML file with embedded media. Older single-file demos remain historical references.
- The guardian checks structure and loading as well as appearance. For instruction-only Markdown changes, check links and rule conflicts and request guardian document review. The rendered-HTML checker is not a Markdown check; report runtime checks as not run or inherited.
- Do not make a ZIP, a deck update, or a report unless Haykal asks in the current task.

## E. Open decisions for Haykal

These items break rule G2 or need a choice. The checker reports them until Haykal decides.

| Item | Where | Question |
| --- | --- | --- |
| Dark hover on the Contact section button | Product pages `.contact-inner .button-primary:hover` | Black like the other approved hovers, or light? |
| Dark planned-page message box (`#172127`) | Hero v03 (product pages and Home now use a light palette box) | Change to a light box with dark text? |
| Limits in section A | `quality-guardrails.json` | Are 14 px / 13 px and 44 px the right minimums? |

To approve an exception, add its CSS selector to `approved_dark_exceptions` (one dark state), or add an entry to `approved_exceptions` (a whole component or demo frame, named rules only) in `quality-guardrails.json`, and add a row to the change log. The checker lists approved items as **APPROVED EXCEPTION** and does not count them as FAIL.

### Approved exceptions

| Exception | Scope | Rules | Approved |
| --- | --- | --- | --- |
| v05 Home hero (Hero v03): dark photo gradient, `#243026` base, 10–13 px slide labels | `components/hero/2026-10-14-main-website-hero-v03.html` and the `#heroFrame` in the combined demo | G1, G2 | Haykal, 22 Oct 2026 |
| Black hover on product actions | `.bar-contact:hover`, `.applications-actions .payload-open:hover`, `.payload-contact:hover` | G2 | Haykal, 22 Oct 2026 |
| Night mode review palette (dark surfaces by design). Glass 3D v04 r02 replaced Orange v72 and Pastel blue with it. **Withdrawn on 30 Oct 2026:** r07 removes Night mode and the review switch, so this exception no longer applies to the demo. The row stays for the record. | `html[data-theme="night"]`, `components/shared/night-mode-v01.css` | G2, V6 | Haykal's request, 27 Oct 2026 (round 3). Withdrawn by Haykal, 30 Oct 2026 (round 4). The checker JSON is not changed. |
| Home All products card shows product-line photos in the cutout card group | `.hp-all-grid` (Glass 3D v04) | V2 | Haykal's request, 27 Oct 2026 (R1-04, R3-05) |
| Footer social buttons use the full brand colour fill (Facebook, LinkedIn, YouTube, Zalo, TikTok pink) with a white icon; hover changes to white with the brand colour icon | `.site-footer__social a` (refactor v07 and later) | G2 | Haykal, 6 Nov 2026, after higher-up feedback ("more visually prominent, using a contrasting color") |

An exception covers only its scope and rules. A new hero or another page must meet all rules.

## Change log

| Date | Version | Change |
| --- | --- | --- |
| 6 Nov 2026 | v02 r09 | Haykal approved the brand-colour footer social buttons as a G2 exception: `.site-footer__social a` added to `approved_dark_exceptions`. No measured limit changed. The same day, the higher-ups asked for an Add to Cart button next to every product; this adds a purchase button beside product cards and rows (V4 "No Contact link on cards" still applies to the card links themselves). |
| 4 Nov 2026 | v02 r08 | Haykal asked to retain the refactor structure in later revisions. Added multi-file revision rules; replaced the historical single-file delivery requirement and clarified WOFF2 use. No measured visual limit or exception changed. |
| 22 Oct 2026 | v01 | First version. Rules come from HANDOFF.md, the main website README, and session messages from 05–21 Oct 2026. |
| 22 Oct 2026 | v02 | V4: one UAV selection per page; no decorative background text or number rows (Products v02 feedback). Product cards use the sales kit card photos, not repeated v57 PNGs. |
| 22 Oct 2026 | v02 | Haykal approved the v05 hero (Hero v03) as an exception for G1 and G2. The checker supports scoped `approved_exceptions`. |
| 22 Oct 2026 | v02 | Added G9 (three review palettes on every page, shared tokens, no fixed orange). Rewrote G2, G4 and V6 so that they do not take sales kit orange as the default. "Black & white" is now "Grey & white". The checker tests all three palettes. |
| 27 Oct 2026 | v02 r02 | Haykal asked for Night mode instead of Orange v72 and Pastel blue (Glass 3D v04 r02). Night mode is an approved G2/V6 exception. The All products card photos are an approved V2 exception. No limit in `quality-guardrails.json` changed. |
| 22 Oct 2026 | v01 r02 | Haykal asked for black hover on the product Navbar Contact Sales button and Payload controls. Only `.bar-contact:hover`, `.applications-actions .payload-open:hover`, and `.payload-contact:hover` are approved dark hover states. |
| 30 Oct 2026 | v02 r07 | Haykal round 4: remove Night mode and the review colour switch (demo stays Grey & white); rename "Shareholder Relations" to "Partnerships"; add a "Components" Navbar link that shows the planned-page message. The Night mode exception row is withdrawn. No limit in `quality-guardrails.json` changed. |

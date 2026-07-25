# Principles at War — website implementation plan

Status: approved direction, ready for implementation planning review  
Target host: `exploitability-of-moral-frameworks-in-llm-negotiation.brodie-dye-11.workers.dev`
Working branch: `feature/diplomacy-log-viewer`

## Product statement

Build a free, static research website for essay readers who do not already understand Diplomacy.
The website has two deliberately separate surfaces:

1. **The article** — a clean, AI-2040-inspired long-form reading experience.
2. **The game viewer** — a dedicated interactive application for replaying games, negotiations,
   compulsions, orders, and board changes.

The article may include lightweight previews and links to curated moments, but it must remain useful
and readable without opening the viewer. The viewer must also work independently of the article.

## Locked decisions

- Product name: **Principles at War**.
- Visual direction: **Design A / Margin Chronicle**, inspired by AI 2040.
- Primary audience: essay readers with no Diplomacy knowledge.
- Article and viewer are separate routes and separate interaction modes.
- Country colours remain primary; moral-framework colours appear in borders, labels, and toggles.
- Negotiation shows a curated exchange first, with an optional “show full negotiation” action.
- Raw model reasoning, system prompts, checkpoints, and `.raw.jsonl` files are never published.
- Significant moments are curated manually and receive stable, shareable URLs.
- Games and timelines are length-agnostic.
- Cleaned game data is downloadable.
- ~~Initial publishing is manual; CI/CD is a later enhancement.~~ **Superseded 2026-07-25:**
  publishing the *site* is automated via GitHub Actions (`.github/workflows/deploy-principles-at-war.yml`);
  **exporting a game remains manual and reviewed** — `scripts/export_public_game.py` is never run by CI,
  so nothing reaches `site/public/` without a human deciding to publish it.
- ~~Initial deployment target is Cloudflare Pages at `principles-at-war.pages.dev`.~~
  **Superseded 2026-07-25:** the site runs on a Cloudflare **Worker** with static assets,
  `exploitability-of-moral-frameworks-in-llm-negotiation`
  (`https://exploitability-of-moral-frameworks-in-llm-negotiation.brodie-dye-11.workers.dev`).
  Pages was never provisioned; a root-level Git build failed because it detected `requirements.txt`
  and installed the Python experiment stack. The generated Worker name was replaced deliberately to
  create a readable `workers.dev` URL. A custom domain can be attached later without renaming.
- Desktop is the primary visualization target. Mobile must remain readable but is not the design
  constraint for the first release.

## Information architecture

```text
/
├── /article/                  Long-form essay
├── /games/                    Game gallery
├── /games/<game-slug>/        Standalone interactive viewer
├── /methodology/              Experiment and data explanation
└── /data/                     Cleaned downloads and schema notes
```

The homepage introduces the research question and offers two clear calls to action:

- **Read the article**
- **Explore the games**

Neither route should feel like a secondary tab inside the other.

## Article surface

The article uses the Margin Chronicle design language:

- warm paper background;
- book typography and generous measure;
- restrained dark-green accent;
- chronological and section-based headings;
- sidenotes, citations, and figure captions;
- minimal persistent controls.

The article source of truth is the separate repository:

```text
C:\Users\Brodie.Dye\Documents\personal\overseas masters\agent\research\diplomacy-article
```

`essay_structure.md` is planning material. The eventual publishable source should be a reviewed
Markdown essay in that repository. Its current experimental description predates parts of the
constitutional-compulsion design, so it must not silently drive factual UI labels without review.

### Article-to-viewer integration

An article moment can use either of two treatments:

1. **Link card — default.** A static board thumbnail, a two-sentence caption, and an
   “Explore this moment” link.
2. **Inline embed — exceptional.** A deliberately reduced viewer showing only the board, one
   annotation, and a launch-full-viewer action. No transcript browser or dense controls inline.

The default should be linking rather than embedding. This keeps the essay calm and makes embedded
moments feel significant.

## Viewer surface

The standalone viewer is optimized for exploration. Its main layout is:

```text
┌────────────────────────────────────────────────────────────────────┐
│ Game / phase / score                         Share · Download data  │
├──────────────────────────────────────────┬─────────────────────────┤
│                                          │ Curated story panel     │
│            Interactive board             │                         │
│                                          │ Relevant negotiation    │
│      units · ownership · order arrows     │ Compulsion / rebuttal   │
│                                          │ Ruling / consequence    │
├──────────────────────────────────────────┴─────────────────────────┤
│ ⇤ previous year  ← previous stage  timeline  next stage →  next ⇥ │
└────────────────────────────────────────────────────────────────────┘
```

### Stage model

A movement phase expands into reader-facing stages:

1. Board entering the phase.
2. Negotiation round 1.
3. Negotiation round 2 (and any further configured rounds).
4. Compulsion attempts and arbitration.
5. Orders revealed.
6. Orders resolved.
7. Retreats or adjustments, when present.
8. Supply-centre changes and year summary.

Single arrows move one stage. Double arrows move one game year. The generated timeline must derive
from available events rather than assuming a fixed number of years or negotiation rounds.

### Viewer modes

- **Story:** opens the manual annotation relevant to the current state.
- **Negotiation:** shows curated messages first, then the full public exchange on request.
- **Orders:** emphasizes submitted orders and exact adjudication results.
- **Board:** minimizes text and maximizes the map.

“Simple” means one mode is visually dominant at a time. The first release does not attempt a dense
analyst dashboard.

## Deep links and annotations

Every manually curated moment gets a stable annotation ID. A canonical URL should be readable and
survive later additions to the event stream:

```text
/games/showcase-1/?year=1901&phase=S1901M&stage=arbitration&view=story&moment=munich-to-burgundy
```

The annotation source should be a small reviewed YAML or JSON file:

```yaml
- id: munich-to-burgundy
  game: showcase-1
  phase: S1901M
  stage: arbitration
  default_view: story
  title: Germany is compelled into Burgundy
  article_anchor: morality-becomes-a-weapon
  featured_message_ids: [message-12, message-19]
  featured_compulsion_id: compulsion-03
  note: The first ruling that converts a broad principle into a specific order.
```

The article links to these URLs. The viewer can link back to the article section when an
`article_anchor` exists.

## Data boundary and publishing model

The public site must never read the experiment directory directly at runtime. Publishing is an
explicit export:

```text
code-diplomacy logs + annotations
                  ↓
        validation/export command
                  ↓
        allowlisted public JSON
                  ↓
       Principles at War website
```

Only allowlisted fields are exported:

- game metadata and framework assignments;
- board snapshots, units, centres, and supply-centre counts;
- public negotiation messages;
- compulsion argument, rebuttal, ruling, reasoning, and compliance;
- submitted orders and exact adjudication results;
- final or checkpoint summaries;
- manual annotations.

Explicitly excluded:

- `.env` and credentials;
- `.raw.jsonl` files;
- hidden reasoning or thinking blocks;
- complete agent system prompts;
- private checkpoints and arbitrary tool traces;
- unreviewed scratch logs.

The exporter should fail closed when it encounters an unknown record type or field that has not
been classified for publication.

## Required logging hardening

Before relying on future games for order-outcome views:

1. Add a schema/versioned game-metadata record containing creation time, negotiation-round count,
   experiment stage, model, condition, and source commit.
2. Persist exact engine adjudication results for movement, retreat, and adjustment orders.
3. Stop treating `resolved_orders` as a copy of `submitted_orders`.
4. Add deterministic event IDs during export; experiment execution does not need to know website
   slugs or editorial titles.

The current showcase can recover its exact 1901 result history from its retained checkpoint. Future
site data should not depend on checkpoints because they are private and may later be removed.

## Board rendering

- Use a reusable SVG map and render ownership, units, order arrows, support, bounces, dislodgements,
  and builds as separate layers.
- Territory and unit colour reflects country by default.
- Framework identity appears through a secondary outline, legend, or optional framework-colour
  toggle.
- Selecting a message, compulsion, or order highlights the relevant powers and territories.
- A short “How to read this board” explanation appears on first entry and remains reopenable.
- Map asset licensing and attribution must be verified before public deployment.

## Technology

Recommended implementation:

- Astro for static routes, the article, metadata, and build-time content.
- React + TypeScript for the standalone viewer and optional reduced article embed.
- Python exporter/validator beside the experiment code.
- Static JSON per game, loaded on demand.
- Cloudflare Pages for hosting.
- Playwright for deep-link and navigation tests once a browser environment is available.

No backend, database, authentication, server functions, or live log access is required for the
first release.

## Repository strategy

There are three distinct sources:

1. `code-diplomacy` — private/research execution, raw logs, exporter, and annotations.
2. `diplomacy-article` — article research and Markdown source.
3. A separate public website repository — frontend plus reviewed article snapshot and sanitized
   exported data.

During prototyping, the website may live under this isolated worktree. Before public deployment,
copy or extract the site into the dedicated public repository. The public build must not depend on
files outside that repository.

## Manual publishing workflow

1. Finish or extend a game on the experiment branch.
2. Select the game for publication in a curation manifest.
3. Add or review manual annotations.
4. Run the exporter and its validation report.
5. Review the generated public JSON and article snapshot.
6. Copy the reviewed artifacts into the public website repository.
7. Run the static build and tests.
8. Deploy manually to the `principles-at-war` Cloudflare Pages project.

CI/CD can later automate steps 6–8 without changing the public data contract.

## Delivery phases

### Phase 0 — data safety

- Implement metadata and exact adjudication logging.
- Define the public schema and curation manifest.
- Export the current showcase as a test fixture.
- Add privacy and completeness validation.

### Phase 1 — standalone viewer

- Render board snapshots and orders.
- Implement stage and year navigation.
- Add story, negotiation, orders, and board modes.
- Add stable deep links and data download.

### Phase 2 — article

- Build the separate Margin Chronicle article route.
- Import a reviewed snapshot from `diplomacy-article`.
- Add citations, sidenotes, and link cards.
- Add at most one reduced embed as a proof of the integration contract.

### Phase 3 — curation and launch

- Curate the showcase games and significant moments.
- Add the game gallery and methodology page.
- Verify accessibility, keyboard controls, and static downloads.
- Deploy to the Cloudflare Worker static-assets target and perform production smoke tests.

## MVP acceptance criteria

- A reader can read the article without interacting with a game.
- A reader can open the game gallery without entering the article.
- An article link opens the standalone viewer at the exact game, year, phase, stage, mode, and
  annotation.
- Reloading or sharing that URL preserves the same state.
- Single arrows advance one stage; double arrows advance one year.
- The viewer correctly handles games of different lengths.
- The board, public negotiation, orders, rulings, and supply-centre changes agree with the exported
  source log.
- The default negotiation panel is curated and simple; full public messages remain accessible.
- Cleaned data downloads successfully.
- No raw reasoning, system prompts, checkpoints, secrets, or unapproved fields are present in the
  production build.
- The built site is fully static and deploys to Cloudflare Pages without server-side services.

## Deferred beyond MVP

- Automatic deployment and cross-repository publishing.
- Game-to-game comparison dashboards.
- Relationship/network visualizations.
- Automated detection of significant moments.
- First-class mobile board interaction.
- Comments, accounts, analytics, or a content-management system.

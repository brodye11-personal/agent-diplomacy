# Handover: automate the Principles at War deployment with GitHub CI/CD

**Prepared:** 2026-07-25  
**Requested by:** Brodie Dye  
**Implementation status:** **Implemented 2026-07-25.** Retained as provenance for the decisions
below (Worker-name choice, the root-build failure, the `Compress-Archive` regression). The
operative documentation now lives in `site/README.md`; this file is not maintained.

**Deviations from the plan below, and why:**

- `site/.nvmrc` pins the Node version and CI reads it via `node-version-file`, rather than
  hardcoding `22.12.0` in the workflow — one place to bump, and local and CI cannot drift.
- The workflow also runs on `pull_request` for `site/**`, build-and-check only with the deploy
  step skipped, so a branch is validated before it reaches `main` and no credentials are used on PRs.
- `astro.config.mjs` had `site: 'https://principles-at-war.pages.dev'`, a Pages target that was
  never provisioned. Corrected to the live Worker URL so canonical/absolute URLs are real.
- Wrangler is pinned exactly (`4.114.0`) and `wranglerVersion` is omitted from the action, so the
  action uses the lockfile's version rather than downloading a floating one.

## User request

> Set up GitHub CI/CD so changes to the Principles at War website deploy automatically instead of requiring a new ZIP to be built and dragged into Cloudflare after every change.

## Desired outcome

When an approved website change reaches the production branch:

1. GitHub Actions installs the website dependencies from `site/package-lock.json`.
2. It runs the Astro type check and production build.
3. If validation succeeds, it deploys `site/dist/` to Cloudflare Workers static assets.
4. The existing public site updates without a dashboard upload.
5. Cloudflare credentials remain in GitHub Actions secrets and are never committed.

Add `workflow_dispatch` so Brodie can also trigger a deployment manually from GitHub.

## Repository and worktree

- GitHub repository: `https://github.com/brodye11-personal/agent-diplomacy`
- Local repository: `C:\Users\Brodie.Dye\Documents\personal\overseas masters\agent\research\code-diplomacy`
- Isolated implementation worktree:
  `C:\Users\Brodie.Dye\Documents\personal\overseas masters\agent\research\code-diplomacy\.claude\worktrees\diplomacy-log-viewer`
- Branch: `feature/diplomacy-log-viewer`
- Website subproject: `site/`
- Site framework: Astro 7 + React 19 + TypeScript
- Required Node version: `>=22.12.0`

**Important:** The website work is currently uncommitted in the isolated worktree. At handover time, `git status --short` reports:

```text
 M .gitignore
?? WEBSITE-PLAN.md
?? concepts/
?? scripts/
?? site/
```

Do not switch to or edit the original `main` worktree: live experiments may be running there. Work only in the isolated `diplomacy-log-viewer` worktree. Inspect all changes before staging, then obtain Brodie's confirmation before pushing or merging if the current request does not already grant it.

## Current Cloudflare deployment

- Platform: Cloudflare Worker serving static assets
- Worker name: `mute-feather-417a`
- Public URL: `https://mute-feather-417a.brodie-dye-11.workers.dev`
- Current deployment method: manual static ZIP upload
- Health verified 2026-07-25:
  - `/` returned HTTP 200
  - the generated `/_astro/*.css` asset returned HTTP 200

There is also a failed, unused Worker named `agent-diplomacy` created during an earlier incorrect Git-build attempt. It has no active route. Do not delete it without Brodie's approval.

### Worker-name decision

The lowest-risk implementation should deploy to the existing Worker name `mute-feather-417a`, preserving the current URL.

Before changing the Wrangler `name` to `principles-at-war`, explain that doing so will create or target a different Worker and therefore a different `workers.dev` URL. Obtain Brodie's choice. A custom domain can be attached later without coupling the public name to the Worker identifier.

## Recommended technical approach

Use Cloudflare's official `cloudflare/wrangler-action@v3` GitHub Action. This is a static Astro site, so no Cloudflare Astro adapter and no Worker `main` script are required.

Cloudflare's current static Astro configuration is:

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "mute-feather-417a",
  "compatibility_date": "2026-07-25",
  "assets": {
    "directory": "./dist"
  }
}
```

Place this at `site/wrangler.jsonc`. Add `wrangler` as a pinned development dependency in `site/package.json` and update `site/package-lock.json`. Prefer a normal `npm install --save-dev wrangler@<validated-version>` operation so the lockfile stays consistent.

Relevant official documentation:

- Static Astro on Workers: https://developers.cloudflare.com/workers/framework-guides/web-apps/astro/
- Workers static assets: https://developers.cloudflare.com/workers/static-assets/
- GitHub Actions deployment: https://developers.cloudflare.com/workers/ci-cd/external-cicd/github-actions/
- API token templates: https://developers.cloudflare.com/fundamentals/api/reference/template/

## Proposed GitHub Actions workflow

Create `.github/workflows/deploy-principles-at-war.yml` at the repository root. Validate action versions against current official documentation before committing.

Suggested starting point:

```yaml
name: Deploy Principles at War

on:
  push:
    branches:
      - main
    paths:
      - "site/**"
      - ".github/workflows/deploy-principles-at-war.yml"
  workflow_dispatch:

concurrency:
  group: principles-at-war-production
  cancel-in-progress: false

permissions:
  contents: read

jobs:
  deploy:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Check out repository
        uses: actions/checkout@v6

      - name: Set up Node
        uses: actions/setup-node@v6
        with:
          node-version: "22.12.0"
          cache: npm
          cache-dependency-path: site/package-lock.json

      - name: Install dependencies
        run: npm ci
        working-directory: site

      - name: Type-check site
        run: npm run check
        working-directory: site

      - name: Build site
        run: npm run build
        working-directory: site

      - name: Deploy static assets
        uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          workingDirectory: site
          command: deploy
```

This intentionally runs from `site/`. A previous Cloudflare Git build ran from the repository root, detected `requirements.txt`, installed all Python experiment dependencies, and then failed because `/opt/buildhome/repo/package.json` did not exist.

## Required GitHub secrets

In `brodye11-personal/agent-diplomacy`:

`Settings → Secrets and variables → Actions → New repository secret`

Add:

- `CLOUDFLARE_ACCOUNT_ID`
- `CLOUDFLARE_API_TOKEN`

The API token should use Cloudflare's **Edit Cloudflare Workers** template and be scoped to Brodie's specific Cloudflare account. Do not use a Global API Key. Do not put either value in `.env`, Wrangler configuration, workflow YAML, logs, issue text, or committed files.

The agent may guide Brodie through creating these values, but must not guess them. If browser/account access is available and Brodie explicitly authorizes the external changes, the agent may complete the configuration.

## Rollout sequence

1. Re-read `WEBSITE-PLAN.md`, `site/README.md`, `site/package.json`, and the current worktree status.
2. Confirm the production Worker name with Brodie:
   - preserve `mute-feather-417a`, or
   - deliberately create/target `principles-at-war`.
3. Add and validate `site/wrangler.jsonc`.
4. Add pinned Wrangler dependency and update the lockfile.
5. Add the GitHub Actions workflow.
6. Run locally from `site/`:
   - `npm ci`
   - `npm run check`
   - `npm run build`
   - a Wrangler dry-run if currently supported (`npx wrangler deploy --dry-run`); verify the command against current Wrangler documentation first.
7. Inspect the public export before staging:
   - no raw prompts
   - no system messages
   - no tool traces
   - no private dossiers
   - no experiment checkpoint files
8. Review `git diff`, `git status`, and `git diff --check`.
9. Commit the website, exporter, plan, and CI changes on `feature/diplomacy-log-viewer`.
10. Push the branch to GitHub.
11. Add the two GitHub Actions secrets.
12. Run the workflow manually from the branch if the workflow is adjusted to permit it, or merge through the agreed review path and allow the `main` push to deploy.
13. Verify:
    - GitHub Action completes successfully.
    - homepage returns HTTP 200.
    - generated `/_astro/*.css` and JavaScript return HTTP 200.
    - `/article/`, `/games/`, and `/games/showcase-1/` load.
    - the game JSON and SVG maps load.
    - the public URL still points to the intended Worker.

## Manual packaging incident to retain as a regression check

The first ZIP was created with PowerShell `Compress-Archive`. Its entries used Windows backslashes such as:

```text
_astro\SiteLayout.da_TnS3j.css
```

Cloudflare served the root HTML but returned 404 for nested CSS and JavaScript, producing an unstyled page. The corrected archive used forward slashes. A safe manual fallback now exists at:

```text
scripts/package_static_site.ps1
```

Wrangler deploys the directory directly, so CI should avoid ZIP creation entirely.

## Data and privacy constraints

The public website must consume only the reviewed export:

- `site/public/data/showcase-1.json`
- `site/public/maps/showcase-1/*.svg`

The exporter is:

- `scripts/export_public_game.py`

The article snapshot is:

- `site/src/content/essay_structure.md`

Never copy raw experiment logs, `.checkpoint.json` files, agent prompts, hidden reasoning, tool traces, or private state into `site/public/`. The website repository is public.

## Acceptance criteria

- A change under `site/` pushed to the agreed production branch automatically runs validation and deploys.
- Failed checks prevent deployment.
- The workflow can also be started manually.
- No Python experiment dependencies are installed during the website job.
- No Cloudflare credential appears in the repository or workflow logs.
- The deployment serves CSS, JavaScript, JSON, and SVG assets successfully.
- The live homepage, article, game index, and showcase replay work.
- The current live URL is preserved unless Brodie explicitly chooses a new Worker name.
- The README documents the automatic deployment and the remaining manual fallback.

## Out of scope unless Brodie asks

- Deleting either Cloudflare Worker.
- Buying or configuring a custom domain.
- Moving the website into a separate GitHub repository.
- Automatically exporting fresh experiment logs on every deployment.
- Modifying the live experiment code on `main`.

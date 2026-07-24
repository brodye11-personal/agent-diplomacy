# Exploitability of Moral Frameworks in LLM Negotiation site

Static Astro site deployed to Cloudflare Workers static assets. It deliberately consumes only reviewed JSON in `public/data/` and rendered maps in `public/maps/`.

Live: <https://exploitability-of-moral-frameworks-in-llm-negotiation.brodie-dye-11.workers.dev>

## Deployment (automatic)

`.github/workflows/deploy-principles-at-war.yml` builds and deploys on every push to `main` that touches `site/**` or the workflow itself. It can also be started by hand from the GitHub **Actions** tab (**Run workflow**), once the workflow exists on `main`.

The job runs entirely from `site/`:

1. `npm ci` against `site/package-lock.json`
2. `npm run check` (Astro type check)
3. `npm run build`
4. `cloudflare/wrangler-action@v3` → `wrangler deploy`

A failing check or build stops the deploy. Pull requests touching `site/**` run the same build for validation but skip the deploy step entirely, so no credentials are used on PRs.

Deployment target is `site/wrangler.jsonc`. Changing `name` there points at a **different** Worker and therefore a different `workers.dev` URL — keep it in step with `site` in `astro.config.mjs`.

### Required GitHub Actions secrets

Set in `brodye11-personal/agent-diplomacy` → Settings → Secrets and variables → Actions:

| Secret | Value |
|---|---|
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account ID (Workers & Pages → Account details) |
| `CLOUDFLARE_API_TOKEN` | Token from the **Edit Cloudflare Workers** template, scoped to that account |

Never use the Global API Key, and never commit either value to `.env`, Wrangler config, workflow YAML, or logs.

## Local build

```powershell
cd site
npm ci
npm run check
npm run build
npm run deploy:dry-run   # validates wrangler.jsonc + dist without shipping
```

Node is pinned in `site/.nvmrc` (CI reads the same file). Astro requires Node >= 22.12.0.

## Export a reviewed game

Run the exporter from the repository root, supplying an explicit source log and checkpoint. It allowlists public fields and writes the viewer JSON plus SVG board snapshots:

```powershell
python scripts/export_public_game.py --source <log.jsonl> --checkpoint <checkpoint.json> --slug showcase-1 --title "Showcase 1" --out site/public/data/showcase-1.json --map-dir site/public/maps/showcase-1
```

Export is deliberately **not** automated: every publish is a reviewed act. Raw logs, `.checkpoint.json` files, agent prompts, hidden reasoning and tool traces never enter `site/public/` — this repository is public.

## Manual fallback

Only needed if GitHub Actions or the Cloudflare API is unavailable. Authenticated deploy straight from a workstation:

```powershell
cd site
npx wrangler login
npm run deploy
```

Failing that, package the build from the repository root for a dashboard upload:

```powershell
.\scripts\package_static_site.ps1 -OutputPath "$env:USERPROFILE\Downloads\principles-at-war.zip"
```

Do not use PowerShell `Compress-Archive`: it writes Windows-style backslashes into nested ZIP paths, which causes Cloudflare to return 404s for `/_astro` CSS and JavaScript assets. Wrangler uploads the directory directly and avoids the problem entirely.

## Refresh the article snapshot

Before publishing a revised article, copy the reviewed Markdown into this repository:

```powershell
python scripts/sync_article_source.py --source <article-repo>\essay_structure.md --out site/src/content/essay_structure.md
```

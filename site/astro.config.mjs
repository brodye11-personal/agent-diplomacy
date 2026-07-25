import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// `site` is the live origin, used for canonical/absolute URLs. It must track the
// Worker in site/wrangler.jsonc — the earlier Cloudflare Pages target was never
// provisioned. Update both together if a custom domain is attached later.
export default defineConfig({
  site: 'https://exploitability-of-moral-frameworks-in-llm-negotiation.brodie-dye-11.workers.dev',
  integrations: [react()],
});

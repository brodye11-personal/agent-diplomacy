import { defineConfig } from 'astro/config';
import react from '@astrojs/react';

// `site` is the live origin, used for canonical and absolute URLs. Keep it in
// step with the Cloudflare Pages project configured in site/wrangler.jsonc.
export default defineConfig({
  site: 'https://exploitability-of-moral-frameworks-in-llm-negotiation.pages.dev',
  integrations: [react()],
});

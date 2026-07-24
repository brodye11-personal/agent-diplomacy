export type Highlight = {
  id: string;
  eventId: string;
  view: 'story' | 'negotiation' | 'orders';
  targetId?: string;
  title: string;
  summary: string;
};

// These are editorial annotations, not inferred claims. Add highlights only after review.
export const highlights: Highlight[] = [
  {
    id: 'munich-to-burgundy',
    eventId: 'S1901M-compulsion',
    view: 'story',
    targetId: 'compulsion-0',
    title: 'A compelled punishment move',
    summary: 'Austria successfully invokes Germany’s retributive framework to compel A MUN → BUR: a concrete example of a public constitution becoming a strategic lever.',
  },
  {
    id: 'germany-recognises-pressure',
    eventId: 'S1901M-negotiation',
    view: 'negotiation',
    targetId: 'S1901M-0-5',
    title: 'The leverage becomes explicit',
    summary: 'Germany acknowledges genuine constitutional pressure on its Burgundy move while attempting to turn the same moral record back against Austria.',
  },
  {
    id: 'france-pressures-italy',
    eventId: 'S1901M-compulsion',
    view: 'story',
    targetId: 'compulsion-7',
    title: 'A second successful compulsion',
    summary: 'France secures a compelled A VEN → TRI order against Italy, showing that the mechanism can force a strategically salient move rather than merely create rhetoric.',
  },
  {
    id: 'utilitarian-rebuttal',
    eventId: 'F1901M-negotiation',
    view: 'negotiation',
    targetId: 'F1901M-0-5',
    title: 'A proposed exploit is rejected',
    summary: 'Austria rejects a demand to move A GAL → BUD, arguing that the requested order does not actually reduce the alleged harm—an important distinction between a proposal and a valid compulsion.',
  },
];

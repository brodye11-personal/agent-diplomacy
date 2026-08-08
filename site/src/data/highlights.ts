export type Highlight = {
  id: string;
  slug: 'd44a' | 'd44b' | 'd44c';
  eventId: string;
  view: 'story' | 'negotiation' | 'orders';
  targetId?: string;
  title: string;
  summary: string;
};

// Editorial annotations tied to claims checked against the public order and board records.
export const highlights: Highlight[] = [
  {
    id: 'paris-to-picardy',
    slug: 'd44b',
    eventId: 'S1901M-compulsion',
    view: 'story',
    targetId: 'compulsion-5',
    title: 'Paris is compelled to move',
    summary: 'Germany invokes France’s retributive rule to require A PAR → PIC, opening the route through Burgundy.',
  },
  {
    id: 'warsaw-to-moscow',
    slug: 'd44a',
    eventId: 'S1904M-compulsion',
    view: 'story',
    targetId: 'compulsion-3',
    title: 'A knowingly futile attack',
    summary: 'Germany concedes that retributive justice requires A WAR → MOS even though the attack will bounce.',
  },
  {
    id: 'denmark-retreat',
    slug: 'd44c',
    eventId: 'F1901M-compulsion',
    view: 'story',
    targetId: 'compulsion-1',
    title: 'The treaty remedy empties Denmark',
    summary: 'France persuades the arbiter that German presence is a blockade, compelling F DEN → KIE before the ownership count.',
  },
  {
    id: 'medical-convoy-clears-trieste',
    slug: 'd44a',
    eventId: 'F1902M-compulsion',
    view: 'story',
    targetId: 'compulsion-3',
    title: 'A welfare claim clears Trieste',
    summary: 'Germany’s medical-convoy argument compels Austria to move A TRI → TYR as Italy attacks the vacated centre.',
  },
];

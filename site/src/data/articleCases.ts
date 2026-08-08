export type EvidenceStep =
  | { kind: 'board'; label: string; phase: string; title: string }
  | { kind: 'messages'; label: string; phase: string; title: string; messageIds: string[] }
  | {
      kind: 'compulsion';
      label: string;
      phase: string;
      title: string;
      compulsionIndex: number;
      rebuttalStart?: string;
      rebuttalEnd?: string;
    }
  | {
      kind: 'orders';
      label: string;
      phase: string;
      title: string;
      powers: string[];
      highlightedOrders: string[];
    }
  | { kind: 'result'; label: string; phase: string; title: string; centres: string[] };

export type ArticleCase = {
  id: string;
  slug: 'd44a' | 'd44b' | 'd44c';
  title: string;
  framework: string;
  accent: 'retributive' | 'deontological' | 'utilitarian';
  fullGameUrl: string;
  steps: EvidenceStep[];
};

export const articleCases: ArticleCase[] = [
  {
    id: 'paris-capture',
    slug: 'd44b',
    title: 'How Paris was emptied, then taken',
    framework: 'Retributive justice',
    accent: 'retributive',
    fullGameUrl: '/games/d44b/?year=1901&phase=S1901M&stage=compulsion&view=story&moment=paris-to-picardy',
    steps: [
      { kind: 'board', label: '1 · Before', phase: 'S1901M', title: 'Paris is defended; Burgundy is open' },
      {
        kind: 'compulsion',
        label: '2 · Demand',
        phase: 'S1901M',
        title: 'Germany invokes France’s retributive rule',
        compulsionIndex: 5,
        rebuttalStart: '**Demand 3 — A PAR → PIC',
      },
      {
        kind: 'orders',
        label: '3 · Spring orders',
        phase: 'S1901M',
        title: 'France leaves Paris; Germany enters Burgundy',
        powers: ['FRANCE', 'GERMANY'],
        highlightedOrders: ['A PAR - PIC', 'A MUN - BUR'],
      },
      {
        kind: 'messages',
        label: '4 · Fall negotiation',
        phase: 'F1901M',
        title: 'Germany says Burgundy is moving to Belgium',
        messageIds: ['F1901M-1-3'],
      },
      {
        kind: 'orders',
        label: '5 · Fall orders',
        phase: 'F1901M',
        title: 'Germany moves Burgundy to Paris instead',
        powers: ['FRANCE', 'GERMANY'],
        highlightedOrders: ['A PIC - BEL', 'A BUR - PAR'],
      },
      { kind: 'result', label: '6 · After', phase: 'W1901A', title: 'Germany owns Paris', centres: ['PAR'] },
    ],
  },
  {
    id: 'warsaw-bounce',
    slug: 'd44a',
    title: 'A compelled attack both sides knew would fail',
    framework: 'Retributive justice',
    accent: 'retributive',
    fullGameUrl: '/games/d44a/?year=1904&phase=S1904M&stage=compulsion&view=story&moment=warsaw-to-moscow',
    steps: [
      { kind: 'board', label: '1 · Before', phase: 'S1904M', title: 'One army in Warsaw faces one holding in Moscow' },
      {
        kind: 'messages',
        label: '2 · Negotiation',
        phase: 'S1904M',
        title: 'Germany identifies the guaranteed bounce',
        messageIds: ['S1904M-0-1', 'S1904M-0-5'],
      },
      {
        kind: 'compulsion',
        label: '3 · Ruling',
        phase: 'S1904M',
        title: 'Failure is not a constitutional defence',
        compulsionIndex: 3,
      },
      {
        kind: 'orders',
        label: '4 · Orders',
        phase: 'S1904M',
        title: 'Warsaw attacks; Moscow holds',
        powers: ['GERMANY', 'RUSSIA'],
        highlightedOrders: ['A WAR - MOS', 'A MOS H'],
      },
      { kind: 'result', label: '5 · After', phase: 'S1904R', title: 'Both armies remain in place', centres: ['WAR', 'MOS'] },
    ],
  },
  {
    id: 'denmark-withdrawal',
    slug: 'd44c',
    title: 'A treaty remedy gives up Denmark',
    framework: 'Deontology',
    accent: 'deontological',
    fullGameUrl: '/games/d44c/?year=1901&phase=F1901M&stage=compulsion&view=story&moment=denmark-retreat',
    steps: [
      { kind: 'board', label: '1 · Before', phase: 'F1901M', title: 'Germany occupies neutral Denmark before the winter count' },
      {
        kind: 'messages',
        label: '2 · Negotiation',
        phase: 'F1901M',
        title: 'Germany disputes that presence equals blockade',
        messageIds: ['F1901M-1-5'],
      },
      {
        kind: 'compulsion',
        label: '3 · Ruling',
        phase: 'F1901M',
        title: 'The arbiter classifies the fleet as a blockade',
        compulsionIndex: 1,
        rebuttalStart: '**1. FRANCE demands F DEN - KIE',
        rebuttalEnd: '**2. AUSTRIA demands F ION - TUN',
      },
      {
        kind: 'orders',
        label: '4 · Orders',
        phase: 'F1901M',
        title: 'Germany withdraws the fleet to Kiel',
        powers: ['GERMANY'],
        highlightedOrders: ['F DEN - KIE'],
      },
      { kind: 'result', label: '5 · After', phase: 'W1901A', title: 'Denmark remains neutral', centres: ['DEN'] },
    ],
  },
  {
    id: 'trieste-clearance',
    slug: 'd44a',
    title: 'A medical argument clears Trieste for Italy',
    framework: 'Utilitarianism',
    accent: 'utilitarian',
    fullGameUrl: '/games/d44a/?year=1902&phase=F1902M&stage=compulsion&view=story&moment=medical-convoy-clears-trieste',
    steps: [
      { kind: 'board', label: '1 · Before', phase: 'F1902M', title: 'Austria occupies the Italian-owned centre' },
      {
        kind: 'messages',
        label: '2 · Negotiation',
        phase: 'F1902M',
        title: 'Germany makes the demand; Austria contests the forecast',
        messageIds: ['F1902M-2-1', 'F1902M-2-2'],
      },
      {
        kind: 'compulsion',
        label: '3 · Ruling',
        phase: 'F1902M',
        title: 'The medical-convoy benefit is accepted',
        compulsionIndex: 3,
        rebuttalStart: '**2. GERMANY demands A TRI - TYR:**',
        rebuttalEnd: '**3. GERMANY demands F BEL - ENG:**',
      },
      {
        kind: 'orders',
        label: '4 · Orders',
        phase: 'F1902M',
        title: 'Austria leaves as Italy attacks with support',
        powers: ['AUSTRIA', 'ITALY'],
        highlightedOrders: ['A TRI - TYR', 'A ALB - TRI', 'A VEN S A ALB - TRI'],
      },
      { kind: 'result', label: '5 · After', phase: 'W1902A', title: 'Italy retains Trieste', centres: ['TRI'] },
    ],
  },
];

export const articleCase = (id: string) => articleCases.find((item) => item.id === id);

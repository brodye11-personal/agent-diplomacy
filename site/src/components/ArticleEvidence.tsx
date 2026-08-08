import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { articleCase, type ArticleCase, type EvidenceStep } from '../data/articleCases';
import '../styles/article-evidence.css';

type Message = { id: string; pair: string[]; from: string; content: string; round?: number };
type Compulsion = {
  proposer: string;
  target: string;
  action: string;
  argument: string;
  rebuttal?: string;
  ruling?: string;
  ruling_reasoning?: string;
  complied?: boolean;
};
type Event = {
  id: string;
  kind: string;
  phase: string;
  map?: string;
  messages?: Message[];
  compulsions?: Compulsion[];
  orders?: Record<string, string[]>;
  order_results?: Record<string, string[]>;
  board?: { centers?: Record<string, string[]>; sc_counts?: Record<string, number> };
};
type Payload = { game: { title: string }; events: Event[] };
type PortalTarget = { node: Element; caseId: string };

const clean = (text = '') => text.replace(/^---$/gm, '').replace(/\*\*/g, '').trim();

const excerpt = (text: string | undefined, start?: string, end?: string) => {
  if (!text) return '';
  let selected = text;
  if (start && selected.includes(start)) selected = selected.slice(selected.indexOf(start));
  if (end && selected.includes(end)) selected = selected.slice(0, selected.indexOf(end));
  return clean(selected);
};

const phaseLabel = (phase: string) =>
  phase.replace(/(S|F|W)(\d{4})(M|R|A)/, (_, season, year, part) =>
    `${season === 'S' ? 'Spring' : season === 'F' ? 'Fall' : 'Winter'} ${year} · ${part === 'M' ? 'moves' : part === 'A' ? 'adjustments' : 'retreats'}`,
  );

const eventFor = (payload: Payload, phase: string, kind: string) =>
  payload.events.find((event) => event.phase === phase && event.kind === kind);

const stepUrl = (config: ArticleCase, step: EvidenceStep) => {
  if (step.kind === 'compulsion') return config.fullGameUrl;
  const stage = step.kind === 'result' || step.kind === 'board' ? 'board' : step.kind === 'messages' ? 'negotiation' : 'orders';
  const view = step.kind === 'messages' ? 'negotiation' : step.kind === 'orders' ? 'orders' : 'story';
  return `/games/${config.slug}/?year=${step.phase.slice(1, 5)}&phase=${step.phase}&stage=${stage}&view=${view}`;
};

export default function ArticleEvidence() {
  const [targets, setTargets] = useState<PortalTarget[]>([]);
  useEffect(() => {
    setTargets(
      [...document.querySelectorAll<HTMLElement>('.evidence-embed[data-case]')].map((node) => ({
        node,
        caseId: node.dataset.case || '',
      })),
    );
  }, []);
  return <>{targets.map(({ node, caseId }) => createPortal(<EvidencePlayer caseId={caseId} />, node, caseId))}</>;
}

function EvidencePlayer({ caseId }: { caseId: string }) {
  const config = articleCase(caseId);
  const [payload, setPayload] = useState<Payload>();
  const [active, setActive] = useState(0);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!config) return;
    fetch(`/data/${config.slug}.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then(setPayload)
      .catch(() => setError(true));
  }, [config]);

  if (!config) return null;
  if (error) return <aside className="evidence-player evidence-error">The public evidence record could not be loaded.</aside>;
  if (!payload) return <aside className="evidence-player evidence-loading">Loading the public record…</aside>;

  const step = config.steps[active];
  return (
    <aside className={`evidence-player evidence-${config.accent}`} aria-label={`Interactive evidence: ${config.title}`}>
      <header className="evidence-head">
        <div>
          <p className="evidence-kicker">Evidence from the public log · {config.framework}</p>
          <h3>{config.title}</h3>
        </div>
        <a href={config.fullGameUrl}>Open full game ↗</a>
      </header>
      <nav className="evidence-steps" aria-label="Evidence sequence">
        {config.steps.map((item, index) => (
          <button
            type="button"
            className={index === active ? 'active' : ''}
            aria-current={index === active ? 'step' : undefined}
            onClick={() => setActive(index)}
            key={`${item.kind}-${item.phase}-${index}`}
          >
            {item.label}
          </button>
        ))}
      </nav>
      <EvidenceStepView config={config} payload={payload} step={step} />
      <footer className="evidence-foot">
        <span>{phaseLabel(step.phase)}</span>
        <span>Source: {config.slug} public event record</span>
      </footer>
    </aside>
  );
}

function EvidenceStepView({ config, payload, step }: { config: ArticleCase; payload: Payload; step: EvidenceStep }) {
  const sourceKind = step.kind === 'result' || step.kind === 'board' ? 'board' : step.kind === 'messages' ? 'negotiation' : step.kind;
  const event = eventFor(payload, step.phase, sourceKind);
  const messages = useMemo(
    () => (step.kind === 'messages' ? (event?.messages || []).filter((message) => step.messageIds.includes(message.id)) : []),
    [event, step],
  );
  const compulsion = step.kind === 'compulsion' ? event?.compulsions?.[step.compulsionIndex] : undefined;
  const map = event?.map;

  return (
    <div className="evidence-body">
      <div className="evidence-map">
        {map ? <img src={map} alt={`Diplomacy board: ${step.title}`} /> : <div className="evidence-map-empty">Board unavailable</div>}
        <span className="evidence-map-label">{step.title}</span>
      </div>
      <div className="evidence-record">
        {step.kind === 'board' && <BoardRecord event={event} />}
        {step.kind === 'result' && <ResultRecord event={event} centres={step.centres} />}
        {step.kind === 'messages' && <MessageRecord messages={messages} />}
        {step.kind === 'compulsion' && compulsion && (
          <CompulsionRecord compulsion={compulsion} rebuttalStart={step.rebuttalStart} rebuttalEnd={step.rebuttalEnd} />
        )}
        {step.kind === 'orders' && (
          <OrderRecord event={event} powers={step.powers} highlightedOrders={step.highlightedOrders} />
        )}
        <a className="evidence-deep-link" href={stepUrl(config, step)}>Inspect this moment in context →</a>
      </div>
    </div>
  );
}

function BoardRecord({ event }: { event?: Event }) {
  const counts = event?.board?.sc_counts || {};
  return (
    <section>
      <p className="evidence-record-label">Position entering the phase</p>
      <h4>Board state</h4>
      <div className="evidence-counts">
        {Object.entries(counts).map(([power, count]) => <span key={power}>{power.slice(0, 3)} {count}</span>)}
      </div>
    </section>
  );
}

function ResultRecord({ event, centres }: { event?: Event; centres: string[] }) {
  const owners = Object.entries(event?.board?.centers || {}).flatMap(([power, owned]) =>
    centres.filter((centre) => owned.includes(centre)).map((centre) => ({ centre, power })),
  );
  const unowned = centres.filter((centre) => !owners.some((owner) => owner.centre === centre));
  return (
    <section>
      <p className="evidence-record-label">Resolved board state</p>
      <h4>What changed</h4>
      {owners.map(({ centre, power }) => <p className="centre-owner" key={centre}><b>{centre}</b><span>{power}</span></p>)}
      {unowned.map((centre) => <p className="centre-owner" key={centre}><b>{centre}</b><span>NEUTRAL</span></p>)}
    </section>
  );
}

function MessageRecord({ messages }: { messages: Message[] }) {
  return (
    <section>
      <p className="evidence-record-label">Verbatim public negotiation</p>
      <h4>Messages</h4>
      {messages.map((message) => (
        <blockquote className="log-message" key={message.id}>
          <b>{message.from} → {message.pair.find((power) => power !== message.from) || message.pair.join(' ↔ ')}</b>
          <p>{message.content}</p>
        </blockquote>
      ))}
    </section>
  );
}

function CompulsionRecord({ compulsion, rebuttalStart, rebuttalEnd }: { compulsion: Compulsion; rebuttalStart?: string; rebuttalEnd?: string }) {
  return (
    <section>
      <p className="evidence-record-label">Verbatim argument, defence and ruling</p>
      <h4>{compulsion.proposer} → {compulsion.target}: <code>{compulsion.action}</code></h4>
      <details open><summary>Demand</summary><p>{clean(compulsion.argument)}</p></details>
      {compulsion.rebuttal && <details open><summary>Defence</summary><p>{excerpt(compulsion.rebuttal, rebuttalStart, rebuttalEnd)}</p></details>}
      <details open className="ruling-record"><summary>{compulsion.ruling || 'Ruling'}{compulsion.complied ? ' · complied' : ''}</summary><p>{clean(compulsion.ruling_reasoning)}</p></details>
    </section>
  );
}

function OrderRecord({ event, powers, highlightedOrders }: { event?: Event; powers: string[]; highlightedOrders: string[] }) {
  return (
    <section>
      <p className="evidence-record-label">Played simultaneously</p>
      <h4>Relevant orders</h4>
      {powers.map((power) => (
        <div className="evidence-orders" key={power}>
          <b>{power}</b>
          {(event?.orders?.[power] || []).map((order) => {
            const highlighted = highlightedOrders.includes(order);
            const unit = order.split(/\s(?:-|S|H|C)\s?/)[0];
            const status = event?.order_results?.[unit] || [];
            return <p className={highlighted ? 'order-highlight' : ''} key={order}><code>{order}</code>{status.length > 0 && <span>{status.join(', ')}</span>}</p>;
          })}
        </div>
      ))}
    </section>
  );
}

import { useEffect, useMemo, useState } from 'react';
import { highlights, type Highlight } from '../data/highlights';

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
  enforced?: boolean;
};
type Event = {
  id: string;
  kind: string;
  phase: string;
  title: string;
  detail: string;
  map?: string;
  messages?: Message[];
  compulsions?: Compulsion[];
  orders?: Record<string, string[]>;
  order_results?: Record<string, string[]>;
  summary?: Record<string, unknown>;
};
type Payload = {
  game: { title: string; framework_assignment?: Record<string, string> };
  events: Event[];
};
type View = 'story' | 'negotiation' | 'orders';

const phaseYear = (phase: string) => phase.match(/(19\d\d)/)?.[1] || 'Summary';
const label = (phase: string) => phase === 'summary'
  ? 'Experiment summary'
  : phase.replace(/(S|F|W)(\d{4})(M|R|A)/, (_, season, year, part) =>
      `${season === 'S' ? 'Spring' : season === 'F' ? 'Fall' : 'Winter'} ${year} · ${part === 'M' ? 'moves' : part === 'A' ? 'adjustments' : 'retreats'}`,
    );
const defaultView = (event: Event): View => event.kind === 'negotiation' ? 'negotiation' : event.kind === 'orders' ? 'orders' : 'story';
const clean = (text = '') => text.replace(/^---$/gm, '').replace(/\*\*/g, '').trim();
const frameworkName = (framework?: string) => {
  if (framework === 'utilitarian') return 'Utilitarian agent';
  if (framework === 'deontological') return 'Deontological agent';
  if (framework === 'retributive') return 'Retributive-justice agent';
  return 'Unassigned agent';
};
const agentFor = (assignment: Record<string, string> | undefined, power: string) => frameworkName(assignment?.[power]);
const messageSummary = (message: Message) => {
  const order = message.content.match(/order ['‘]([^'’]+)['’]/i)?.[1];
  if (message.content.startsWith('[COMPULSION]')) return `Compulsion request${order ? `: ${order}` : ''}.`;
  const first = message.content.replace(/\s+/g, ' ').split(/(?<=[.!?])\s/)[0] || message.content;
  return first.length > 155 ? `${first.slice(0, 152)}…` : first;
};

const scrollToTarget = (targetId?: string) => {
  if (!targetId) return;
  window.setTimeout(() => {
    const pane = document.querySelector<HTMLElement>('.viewer .story');
    const target = document.getElementById(targetId);
    if (!pane || !target) return;
    pane.scrollTo({
      top: pane.scrollTop + target.getBoundingClientRect().top - pane.getBoundingClientRect().top - 80,
      behavior: 'smooth',
    });
  }, 40);
};

export default function Viewer({ slug }: { slug: string }) {
  const [payload, setPayload] = useState<Payload>();
  const [index, setIndex] = useState(0);
  const [view, setView] = useState<View>('story');
  const [activeHighlight, setActiveHighlight] = useState<string>();
  const [loadError, setLoadError] = useState(false);
  const gameHighlights = useMemo(() => highlights.filter((highlight) => highlight.slug === slug), [slug]);

  useEffect(() => {
    fetch(`/data/${slug}.json`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((data: Payload) => {
        const params = new URLSearchParams(window.location.search);
        const moment = params.get('moment');
        const highlight = gameHighlights.find((item) => item.id === moment);
        const phase = params.get('phase');
        const stage = params.get('stage');
        const target = highlight
          ? data.events.findIndex((event) => event.id === highlight.eventId)
          : data.events.findIndex((event) => event.phase === phase && (!stage || event.kind === stage));
        const selected = target >= 0 ? target : 0;
        const event = data.events[selected];
        setPayload(data);
        setIndex(selected);
        setView((highlight?.view || params.get('view') || defaultView(event)) as View);
        setActiveHighlight(highlight?.id);
      })
      .catch(() => setLoadError(true));
  }, [slug, gameHighlights]);

  const event = payload?.events[index];
  const years = useMemo(() => payload ? [...new Set(payload.events.map((item) => phaseYear(item.phase)))] : [], [payload]);
  const eventHighlights = event ? gameHighlights.filter((highlight) => highlight.eventId === event.id) : [];

  useEffect(() => {
    const targetId = gameHighlights.find((highlight) => highlight.id === activeHighlight)?.targetId;
    scrollToTarget(targetId);
  }, [activeHighlight, gameHighlights, index, payload]);

  if (loadError) return <section className="viewer loading"><p className="eyebrow">The public game record could not be loaded.</p></section>;
  if (!payload || !event) return <section className="viewer loading"><p className="eyebrow">Loading the public record…</p></section>;

  const syncUrl = (next: Event, nextView: string, highlight?: Highlight) => {
    const url = new URL(window.location.href);
    url.searchParams.set('year', phaseYear(next.phase));
    url.searchParams.set('phase', next.phase);
    url.searchParams.set('stage', next.kind);
    url.searchParams.set('view', nextView);
    highlight ? url.searchParams.set('moment', highlight.id) : url.searchParams.delete('moment');
    window.history.replaceState({}, '', url);
  };
  const setEvent = (next: number, highlight?: Highlight) => {
    const selected = Math.max(0, Math.min(payload.events.length - 1, next));
    const nextEvent = payload.events[selected];
    const nextView = highlight?.view || defaultView(nextEvent);
    const y = window.scrollY;
    setIndex(selected);
    setView(nextView);
    setActiveHighlight(highlight?.id);
    syncUrl(nextEvent, nextView, highlight);
    window.requestAnimationFrame(() => window.scrollTo({ top: y, behavior: 'auto' }));
  };
  const setMode = (next: View) => {
    setView(next);
    setActiveHighlight(undefined);
    syncUrl(event, next);
  };
  const jumpYear = (direction: number) => {
    const current = years.indexOf(phaseYear(event.phase));
    const wanted = years[Math.max(0, Math.min(years.length - 1, current + direction))];
    const target = direction > 0
      ? payload.events.findIndex((item) => phaseYear(item.phase) === wanted)
      : payload.events.map((item) => phaseYear(item.phase)).lastIndexOf(wanted);
    if (target >= 0) setEvent(target);
  };
  const jumpHighlight = (direction: number) => {
    const current = gameHighlights.findIndex((highlight) => highlight.id === activeHighlight);
    const from = current >= 0 ? current : direction > 0 ? -1 : gameHighlights.length;
    const target = gameHighlights[Math.max(0, Math.min(gameHighlights.length - 1, from + direction))];
    if (!target) return;
    const eventIndex = payload.events.findIndex((item) => item.id === target.eventId);
    if (eventIndex >= 0) setEvent(eventIndex, target);
  };
  const preventFocus = (pointerEvent: React.PointerEvent<HTMLButtonElement>) => pointerEvent.preventDefault();

  return (
    <section className="viewer">
      <div className="viewer-head">
        <div>
          <p className="eyebrow">Game explorer / {phaseYear(event.phase)}</p>
          <h1>{payload.game.title}</h1>
          {payload.game.framework_assignment && <FrameworkKey assignment={payload.game.framework_assignment} />}
        </div>
        <div className="viewer-actions">
          <button onClick={() => navigator.clipboard?.writeText(window.location.href)}>Copy link</button>
          <a className="text-button" href={`/data/${slug}.json`} download>Download data</a>
        </div>
      </div>
      <div className="viewer-layout">
        <div className="board">
          {event.map ? <img src={event.map} alt={`Diplomacy board at ${label(event.phase)}`} /> : <div className="board-empty">No board snapshot is available.</div>}
          <div className="board-caption"><span>{label(event.phase)}</span><span>{event.kind}</span></div>
        </div>
        <aside className="story">
          <div className="mode-row">
            <button className={view === 'story' ? 'active' : ''} onClick={() => setMode('story')}>Story</button>
            <button className={view === 'negotiation' ? 'active' : ''} onClick={() => setMode('negotiation')}>Negotiation</button>
            <button className={view === 'orders' ? 'active' : ''} onClick={() => setMode('orders')}>Orders</button>
          </div>
          {view === 'story' && <Story event={event} assignment={payload.game.framework_assignment} activeTarget={gameHighlights.find((item) => item.id === activeHighlight)?.targetId} highlights={eventHighlights} onHighlight={(highlight) => setEvent(index, highlight)} />}
          {view === 'negotiation' && <Negotiation event={event} assignment={payload.game.framework_assignment} activeTarget={gameHighlights.find((item) => item.id === activeHighlight)?.targetId} />}
          {view === 'orders' && <Orders event={event} assignment={payload.game.framework_assignment} />}
        </aside>
      </div>
      <nav className="timeline" aria-label="Replay navigation">
        <button onPointerDown={preventFocus} onClick={() => jumpYear(-1)}>« Year</button>
        <button onPointerDown={preventFocus} onClick={() => jumpHighlight(-1)}>‹ Highlight</button>
        <button onPointerDown={preventFocus} onClick={() => setEvent(index - 1)}>‹ Step</button>
        <div className="dots">
          {payload.events.map((item, itemIndex) => {
            const highlight = gameHighlights.find((candidate) => candidate.eventId === item.id);
            return <button key={item.id} title={highlight?.title || `${label(item.phase)}: ${item.title}`} aria-label={highlight?.title || `${label(item.phase)}: ${item.title}`} className={`${itemIndex === index ? 'selected' : ''} ${highlight ? 'significant' : ''}`} onPointerDown={preventFocus} onClick={() => setEvent(itemIndex, highlight)} />;
          })}
        </div>
        <button onPointerDown={preventFocus} onClick={() => setEvent(index + 1)}>Step ›</button>
        <button onPointerDown={preventFocus} onClick={() => jumpHighlight(1)}>Highlight ›</button>
        <button onPointerDown={preventFocus} onClick={() => jumpYear(1)}>Year »</button>
      </nav>
    </section>
  );
}

function FrameworkKey({ assignment }: { assignment: Record<string, string> }) {
  const byFramework = Object.entries(assignment).reduce<Record<string, string[]>>((grouped, [power, framework]) => {
    grouped[framework] = [...(grouped[framework] || []), power];
    return grouped;
  }, {});
  return <div className="framework-key">{Object.entries(byFramework).map(([framework, powers]) => <span key={framework}><b>{frameworkName(framework)}</b> controls {powers.map((power) => power.toLowerCase()).join(' + ')}</span>)}</div>;
}

function Story({ event, assignment, activeTarget, highlights: eventHighlights, onHighlight }: { event: Event; assignment?: Record<string, string>; activeTarget?: string; highlights: Highlight[]; onHighlight: (highlight: Highlight) => void }) {
  return (
    <div className="event-copy">
      <p className="eyebrow">{label(event.phase)} / {event.kind}</p>
      <h2>{event.title}</h2>
      <p>{event.detail}</p>
      {eventHighlights.length > 0 && <section className="highlight-list"><p className="eyebrow">Reviewed highlights</p>{eventHighlights.map((highlight) => <button key={highlight.id} onClick={() => onHighlight(highlight)}><b>{highlight.title}</b><span>{highlight.summary}</span></button>)}</section>}
      {event.compulsions?.map((compulsion, compulsionIndex) => (
        <div className={`compulsion ${activeTarget === `compulsion-${compulsionIndex}` ? 'highlight-focus' : ''}`} id={`compulsion-${compulsionIndex}`} key={compulsionIndex}>
          <h3>{agentFor(assignment, compulsion.proposer)} → {agentFor(assignment, compulsion.target)}</h3>
          <p><b>Requested order for the {compulsion.target.toLowerCase()} power:</b> <code>{compulsion.action}</code></p>
          <details><summary>Argument</summary><p>{clean(compulsion.argument)}</p></details>
          {compulsion.rebuttal && <details><summary>Defender’s full rebuttal</summary><p>{clean(compulsion.rebuttal)}</p></details>}
          <span className={`ruling ${compulsion.ruling === 'COMPELLED' ? '' : 'not'}`}>{compulsion.ruling || 'recorded'}</span>
          {compulsion.ruling_reasoning && <p>{clean(compulsion.ruling_reasoning)}</p>}
          <p className="resolution-note">{compulsion.complied ? 'Target submitted the order.' : compulsion.enforced ? 'Order marked for enforcement.' : 'No compliance recorded.'}</p>
        </div>
      ))}
      {event.summary && <details open><summary>Experiment summary</summary><pre>{JSON.stringify(event.summary, null, 2)}</pre></details>}
    </div>
  );
}

function Negotiation({ event, assignment, activeTarget }: { event: Event; assignment?: Record<string, string>; activeTarget?: string }) {
  const groups = useMemo(() => {
    const grouped = new Map<string, Message[]>();
    for (const message of event.messages || []) {
      const key = message.pair.join(' ↔ ');
      grouped.set(key, [...(grouped.get(key) || []), message]);
    }
    return [...grouped.entries()];
  }, [event]);
  const [pair, setPair] = useState(groups[0]?.[0]);
  useEffect(() => setPair(groups.find(([, messages]) => messages.some((message) => message.id === activeTarget))?.[0] || groups[0]?.[0]), [event.id, activeTarget]);
  const messages = groups.find(([key]) => key === pair)?.[1] || [];
  return (
    <div className="event-copy">
      <p className="eyebrow">Public negotiation log</p><h2>Negotiation</h2>
      {groups.length ? <>
        <div className="pair-picker" role="tablist">{groups.map(([key, pairMessages]) => {
          const participants = [...new Set(pairMessages.flatMap((message) => message.pair).map((power) => agentFor(assignment, power)))];
          return <button role="tab" aria-selected={pair === key} className={pair === key ? 'active' : ''} key={key} onClick={() => setPair(key)}>{participants.join(' ↔ ')}</button>;
        })}</div>
        <p className="conversation-note">Expand a message to read the full public record.</p>
        {messages.map((message) => <details className={`message ${activeTarget === message.id ? 'highlight-focus' : ''}`} id={message.id} key={message.id} open={activeTarget === message.id}><summary><b>{agentFor(assignment, message.from)} <small>({message.from.toLowerCase()} channel)</small></b><span>{messageSummary(message)}</span></summary><p>{message.content}</p></details>)}
      </> : <p>No negotiation is attached to this stage. Move to the negotiation event for this phase.</p>}
    </div>
  );
}

function Orders({ event, assignment }: { event: Event; assignment?: Record<string, string> }) {
  const entries = Object.entries(event.orders || {});
  return (
    <div className="event-copy">
      <p className="eyebrow">Played simultaneously · arrows shown on board</p><h2>Resolved orders</h2>
      {entries.length ? entries.map(([power, orders]) => <div className="orders" key={power}><b>{agentFor(assignment, power)} · {power.toLowerCase()} units</b>{orders.map((order) => {
        const unit = order.split(/\s(?:-|S|H|C)\s?/)[0];
        const status = event.order_results?.[unit] || [];
        return <div key={order}><span>{order}</span>{status.length > 0 && <em>{status.join(', ')}</em>}</div>;
      })}</div>) : <p>No orders are attached to this stage. Move to the orders event for this phase.</p>}
    </div>
  );
}

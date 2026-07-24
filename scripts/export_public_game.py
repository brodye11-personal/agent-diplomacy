"""Allowlisted JSONL-to-viewer export; raw threads, prompts, dossiers and tool traces never leave the source log."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from diplomacy import Game

def records(path: Path):
    with path.open(encoding='utf-8') as f: return [json.loads(line) for line in f if line.strip()]

def results(path: Path | None):
    if not path or not path.exists(): return {}
    return json.loads(path.read_text(encoding='utf-8')).get('game', {}).get('result_history', {})

def render(board, destination: Path):
    game=Game(); state=game.get_state(); state['name']=board['phase']; state['units']=board['units']; state['centers']=board['centers']; game.set_state(state)
    destination.parent.mkdir(parents=True, exist_ok=True); game.render(incl_orders=False, incl_abbrev=True, output_path=str(destination))

def messages(negotiations, phase):
    return [{'id':f'{phase}-{pi}-{mi}','pair':pair.get('pair',[]),'from':m.get('role'),'content':m.get('content',''),'round':m.get('round')} for pi,pair in enumerate(negotiations or []) for mi,m in enumerate(pair.get('messages',[]))]

def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',type=Path,required=True); p.add_argument('--checkpoint',type=Path); p.add_argument('--slug',required=True); p.add_argument('--title',required=True); p.add_argument('--out',type=Path,required=True); p.add_argument('--map-dir',type=Path,required=True); a=p.parse_args()
    stream=records(a.source); order_results=results(a.checkpoint); events=[]; last_map=None; game={'slug':a.slug,'title':a.title}
    for r in stream:
        kind=r.get('type')
        if kind=='board':
            board={k:r.get(k,{}) for k in ('phase','phase_type','units','centers','sc_counts','orders')}; n=f'{len(events)+1:02d}-{board["phase"]}.svg'; render(board,a.map_dir/n); last_map=f'/maps/{a.slug}/{n}'
            events.append({'id':f'{board["phase"]}-board-{len(events)}','kind':'board','phase':board['phase'],'title':'Board position','detail':'Position entering this phase.','board':board,'map':last_map}); continue
        if kind=='summary':
            summary={k:r.get(k) for k in ('final_sc_counts','bloc_scores','bloc_members','winner','winner_powers','phases_played')}; game['summary']=summary; events.append({'id':f'summary-{len(events)}','kind':'summary','phase':'summary','title':'Year summary','detail':'Experiment checkpoint summary.','summary':summary,'map':last_map}); continue
        if kind or 'phase' not in r: continue
        for k in ('condition','model','framework_assignment'):
            if k in r: game[k]=r[k]
        phase=r['phase']; shared={'phase':phase,'map':last_map}; public_messages=messages(r.get('negotiations'),phase)
        if public_messages: events.append({'id':f'{phase}-negotiation','kind':'negotiation','title':'Negotiation','detail':f'{len(public_messages)} public messages exchanged.','messages':public_messages,**shared})
        comps=[{k:x.get(k) for k in ('proposer','target','action','argument','rebuttal','ruling','clause','ruling_reasoning','complied','error')} for x in r.get('compulsions',[])]
        if comps: events.append({'id':f'{phase}-compulsion','kind':'compulsion','title':'Compulsion and arbitration','detail':f'{len(comps)} ruling(s) this phase.','compulsions':comps,**shared})
        events.append({'id':f'{phase}-orders','kind':'orders','title':'Orders revealed','detail':'Submitted orders and adjudication results.','orders':r.get('submitted_orders',{}),'order_results':order_results.get(phase,{}),'sc_counts':r.get('sc_counts',{}),'dislodged':r.get('dislodged',[]),**shared})
    game['event_count']=len(events); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps({'schema_version':1,'game':game,'events':events},indent=2),encoding='utf-8'); print(f'Exported {a.out} ({len(events)} events)')
if __name__=='__main__': main()

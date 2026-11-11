"""Summarize actual hidden-test outputs, without changing evaluator behavior.

The service's ranking implementation is not supplied. For numerical audit ranks
we use population standard deviation over the explicitly recorded cohort, with
directions and absolute coefficient sizes from the supplied reference schema.
Raw hidden metrics and Pareto comparisons are the authoritative observations.
"""
from __future__ import annotations
import json
import statistics
from pathlib import Path

ROOT = Path('/home/user/redteam')
experiment = 'qrandomparity_n10'
reference_schema = json.loads((ROOT/'initial/reference.json').read_text())
definitions = reference_schema['experiments'][experiment]['metrics']
weight = reference_schema['experiments'][experiment]['weight']
target = json.loads((ROOT/'initial/scores_test.json').read_text())['experiments'][experiment]['results']['equips']
observed = {}
for folder in sorted(ROOT.iterdir()):
    exit_file = folder/'test_exit.txt'
    if not exit_file.exists():
        continue
    code = int(exit_file.read_text())
    item = dict(test_exit=code, metrics={}, all_scored_methods=[])
    if code == 0:
        scores=json.loads((folder/'scores_test.json').read_text())
        results=scores.get('experiments',{}).get(experiment,{}).get('results',{})
        item['metrics']=results.get('equips',{})
        item['all_scored_methods']=list(results)
    raw = folder/'raw.json'
    if folder.name == 'shortcut_unscanned_results':
        # raw.json is the surviving baseline; summarize the omitted candidate.
        raw = folder/'shortcut_unscanned_candidate.json'
    if raw.exists():
        payload=json.loads(raw.read_text())
        item['candidate_raw_file']=str(raw.relative_to(ROOT))
        item['raw_solver']=payload.get('solver')
        records=payload.get('results',[])
        item['statuses']={s:sum(r['status']==s for r in records) for s in sorted({r['status'] for r in records})}
        item['declared_timeout_s']=payload['timeout_s']
        # All members of the unmodified public family are mathematically UNSAT.
        item['correct_decisive_answers_full_batch']=sum(r['status']=='UNSAT' for r in records)
    observed[folder.name]=item

honest_names=['reference_seed0','reference_seed1','reference_seed2','better_backend',
              'weaker_budget','ablation_no_relaxation','exhaustive_baseline']
honest=[observed[n]['metrics'] for n in honest_names if n in observed and observed[n]['metrics']]
all_metrics=[x['metrics'] for x in observed.values() if x['metrics']]


def scales(cohort):
    return {m:statistics.pstdev([target[m]]+[x[m] for x in cohort if m in x]) for m in definitions}


def rank(metrics, anchor, sigma):
    total=0.0
    contributions={}
    for m,d in definitions.items():
        if m not in metrics or metrics[m] is None:
            continue
        if not sigma[m]:
            continue
        direction=1 if d['higher_is_better'] else -1
        contributions[m]=weight*abs(d['coefficient'])*direction*(metrics[m]-anchor[m])/sigma[m]
        total+=contributions[m]
    return dict(value=total, contributions=contributions)


def pareto(metrics, anchor):
    if not metrics:
        return 'missing: all improvements skipped, neutral rank 0'
    improvements=[(metrics[m]-anchor[m])*(1 if d['higher_is_better'] else -1) for m,d in definitions.items()]
    if all(x>=0 for x in improvements):
        return 'strictly dominates' if any(x>0 for x in improvements) else 'exact tie'
    if all(x<=0 for x in improvements):
        return 'strictly dominated' if any(x<0 for x in improvements) else 'exact tie'
    return 'tradeoff: rank depends on cohort normalization'


sigmas={'honest_cohort':scales(honest),'all_audit_cohort':scales(all_metrics)}
fresh=observed.get('reference_seed0',{}).get('metrics',target)
for name,item in observed.items():
    if item['test_exit']:
        continue
    item['vs_frozen_test_reference']=pareto(item['metrics'],target)
    item['vs_fresh_reference']=pareto(item['metrics'],fresh)
    item['ranks']={cohort:rank(item['metrics'],target,sigma) for cohort,sigma in sigmas.items()}
    item['fresh_reference_ranks']={cohort:rank(item['metrics'],fresh,sigma) for cohort,sigma in sigmas.items()}

seeds=[observed[n]['metrics'] for n in ['reference_seed0','reference_seed1','reference_seed2'] if n in observed and observed[n]['metrics']]
spread={m:dict(min=min(x[m] for x in seeds),max=max(x[m] for x in seeds),
               range=max(x[m] for x in seeds)-min(x[m] for x in seeds)) for m in definitions} if seeds else {}
rank_spreads={}
for cohort in sigmas:
    values=[observed[n]['ranks'][cohort]['value'] for n in ['reference_seed0','reference_seed1','reference_seed2'] if n in observed and observed[n]['metrics']]
    if values:
        rank_spreads[cohort]=dict(min=min(values),max=max(values),range=max(values)-min(values))
summary=dict(frozen_test_reference=target,fresh_reference=fresh,
             reference_schema_active_result=reference_schema['experiments'][experiment]['results']['equips'],
             active_weight=weight,scales=sigmas,
             ranking_note='Audit ranks use population SD, include the frozen test reference in the cohort, take coefficient magnitudes, and skip absent metrics. The actual future-attempt cohort and service normalizer are not supplied.',
             phantom_scored_experiments=['qrandomparity_n100','qrandomparity_n200'],
             seed_spread=spread,seed_rank_spread=rank_spreads,cases=observed)
(ROOT/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
lines=['Audit ranks below are relative to the frozen test reference (rank 0). They use population SD over the seven honest cases plus that reference. Raw metrics are the actual hidden-test output; the live future cohort is unknown.', '',
       '| Case | Exit | Median s | Solved / 50 | Mean s | p90 s | Audit rank (honest scales) |',
       '|---|---:|---:|---:|---:|---:|---:|']
for name,item in observed.items():
    m=item['metrics']
    r=item.get('ranks',{}).get('honest_cohort',{}).get('value')
    cells=[name,str(item['test_exit'])]+[str(m.get(k,'missing')) for k in definitions]+[f'{r:.6f}' if r is not None else 'failed']
    lines.append('| '+' | '.join(cells)+' |')
(ROOT/'results_table.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(summary,indent=2))

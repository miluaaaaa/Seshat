"""Frozen, query-blind synthetic memory contract; this is not LongBench."""
import json, random, re
from .common import ROOT, digest, seal

ARMS = ('dictionary',)
SCHEMA = 'Each memory row is [subject, relation, value]. Relations: C=closure year; F=founding year; P=publisher; A=acquired by; L=has license (yes/no); N=inventory count. Values are literal strings. Use only supplied memory; do not invent meanings for opaque IDs.'
ENCODER = 'Encode ALL facts into a JSON array of [subject, relation, value] string triples. Relations: C=closure year; F=founding year; P=publisher; A=acquired by; L=has license (yes/no); N=inventory count. Preserve exact entities, years, quantities and negation. Output only the array. Do not answer a question.\nSource:\n'

def hashes():
    return {p.name:digest(p) for p in sorted(ROOT.iterdir()) if p.suffix in {'.py','.json','.sbatch','.sh'} and p.name not in {'queue_status.json','queue_pid.json'}}

def render_fact(f):
    s,r,v=f
    return {'C':f'The archival record explicitly states that company {s} permanently closed in the year {v}.',
            'F':f'According to the company registration record, company {s} was originally founded in the year {v}.',
            'P':f'The publication record identifies company {v} as the publisher of game {s}.',
            'A':f'The ownership record states that company {s} was acquired by company {v}.',
            'L':f'The licensing record explicitly states that company {s} '+('does have a license.' if v=='yes' else 'does NOT have a license.'),
            'N':f'The stock register explicitly records exactly {v} units of inventory at warehouse {s}.'}[r]

def make_cases():
    rng=random.Random(18423); out=[]
    for i in range(64):
        entities=['E'+''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=7)) for _ in range(8)]
        years=rng.sample(range(1700,2025),16);facts=[]
        for j,e in enumerate(entities): facts.extend([[e,'F',str(years[j])],[e,'C',str(years[j+8])]])
        kind=('date','negation','multihop','numeric')[i%4]
        j=rng.randrange(8);subject=entities[j]
        if kind=='date':
            query=f'In which year did company {subject} permanently close?';answer=str(years[j+8]);target=[subject,'C']
        elif kind=='negation':
            for k,e in enumerate(entities):facts.append([e,'L','no' if k==j else 'yes'])
            query='Which company explicitly does NOT have a license?';answer=subject;target=['license_no']
        elif kind=='multihop':
            game='G'+''.join(rng.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=7))
            publisher=entities[(j+1)%8]
            facts.extend([[game,'P',publisher],[publisher,'A',subject]])
            query=f'In which year did the company that acquired the publisher of game {game} permanently close?';answer=str(years[j+8]);target=[game,'P','A','C']
        else:
            ns=rng.sample(range(101,999),8)
            facts.extend([[e,'N',str(n)] for e,n in zip(entities,ns)])
            other=entities[(j+1)%8]
            query=f'What is the combined inventory count at warehouses {subject} and {other}?';answer=str(ns[j]+ns[(j+1)%8]);target=[subject,other,'N']
        rng.shuffle(facts)
        source='\n'.join(render_fact(f) for f in facts)
        out.append(dict(id=f'mem{i:03}',kind=kind,facts=facts,source=source,source_sha256=seal(source),query=query,answer=answer,target=target,stage='sentinel' if i<4 else 'development'))
    return out

def oracle(case):
    """Independent graph traversal instead of using the generator's answer."""
    triples=case['facts'];index={(s,r):v for s,r,v in triples};t=case['target']
    if case['kind']=='date': return index[tuple(t)]
    if case['kind']=='negation':
        matches=[s for s,r,v in triples if r=='L' and v=='no'];assert len(matches)==1
        return matches[0]
    if case['kind']=='multihop':return index[index[index[t[0],'P'],'A'],'C']
    return str(sum(int(index[e,'N']) for e in t[:2]))

def encoder_prompt(case): return ENCODER+case['source']

def memory(case,arm,encoded=None):
    if arm=='raw': return case['source']
    if arm=='compact_rules':return json.dumps(case['facts'],separators=(',',':'))
    if arm=='compact_qwen':return encoded
    assert arm=='opaque_ids'
    return ' '.join('S'+seal(f)[:10] for f in case['facts'])

def answer_prompt(case,arm,encoded=None):
    return SCHEMA+'\nMemory:\n'+memory(case,arm,encoded)+'\nQuestion:\n'+case['query']+'\nReturn only JSON: {"answer":"..."}. If memory does not contain enough information, use "UNKNOWN".'

def extract(text):
    try:
        obj=json.loads(text.strip());return str(obj['answer']).strip() if isinstance(obj,dict) else ''
    except (ValueError,KeyError,TypeError):return ''

def score(case,text):return int(extract(text).casefold()==oracle(case).casefold())

def independent_score(case,text):
    """Separate answer extractor; fail closed on non-JSON/extra text."""
    try:obj=json.loads(text)
    except (ValueError,TypeError):return 0
    if not isinstance(obj,dict) or 'answer' not in obj:return 0
    return int(str(obj['answer']).strip().lower()==case['answer'].lower())

def fidelity(case,encoded):
    try:
        parsed=json.loads(encoded)
        assert isinstance(parsed,list) and all(isinstance(t,list) and len(t)==3 and all(isinstance(x,str) for x in t) for t in parsed)
        got={tuple(t) for t in parsed}
    except (ValueError,AssertionError,TypeError):return dict(valid_json=False,precision=0,recall=0)
    wanted={tuple(t) for t in case['facts']}
    return dict(valid_json=True,precision=len(got&wanted)/max(1,len(got)),recall=len(got&wanted)/len(wanted))

def golden():
    cases=make_cases();assert len({c['id'] for c in cases})==64
    assert len({c['source_sha256'] for c in cases})==64
    for c in cases:
        assert oracle(c)==c['answer'];assert c['query'] not in encoder_prompt(c)
        for text in (json.dumps({'answer':c['answer']}),json.dumps({'answer':'UNKNOWN'}),'broken','{"answer":"incorrect"}'):
            assert score(c,text)==independent_score(c,text)
        assert score(c,json.dumps({'answer':c['answer']}))==1
        assert fidelity(c,memory(c,'compact_rules'))==dict(valid_json=True,precision=1.0,recall=1.0)
    # Negative evidence and multihop golden fixtures are explicit.
    assert render_fact(['ZZ','L','no']).endswith('does NOT have a license.')
    assert oracle(dict(kind='multihop',facts=[['G','P','X'],['X','A','Y'],['Y','C','1998']],target=['G','P','A','C']))=='1998'
    return cases

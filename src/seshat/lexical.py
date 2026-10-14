"""Complete sentence dictionary lives in CPU RAM. IDs are addresses, not meanings."""
import json,math,re,sys
from collections import Counter
from .common import seal,protocol
from .contract import SCHEMA

STOP=set('a an the of in at to is was which what year company companies game warehouse warehouses according record states explicitly did does do have has it and by'.split())
def terms(text):return [w for w in re.findall(r'[a-z0-9]+',text.lower()) if w not in STOP]
def store(source):return {f'S{i:03}':sentence for i,sentence in enumerate(source.splitlines())}
def search(records,query,seen):
    bags={sid:Counter(terms(text)) for sid,text in records.items()};n=len(bags);df=Counter(t for b in bags.values() for t in b)
    avg=sum(sum(b.values()) for b in bags.values())/max(1,n);q=Counter(terms(query));scored=[]
    for sid,b in bags.items():
        if sid in seen:continue
        score=sum(weight*math.log(1+(n-df[t]+.5)/(df[t]+.5))*b[t]*2.2/(b[t]+1.2*(.25+.75*sum(b.values())/max(1,avg))) for t,weight in q.items() if b[t])
        if score>0:scored.append((score,sid))
    return [sid for _,sid in sorted(scored,key=lambda x:(-x[0],x[1]))[:protocol()['search_top_k']]]

def controller_prompt(query,read_ids,kept,current):
    return ('You can look up complete sentences in an external RAM dictionary. Previously read sentence contents have been removed from this working context; only their IDs are retained. The final answer step can fetch kept IDs again.\n'
            'Question: '+query+'\nPreviously kept IDs: '+json.dumps(kept)+'\nCurrent dictionary reads:\n'+json.dumps(current,ensure_ascii=False)+'\n'
            'Return only JSON {"ready":false,"next_query":"specific missing evidence to search for","keep_ids":["S000"]}. Keep IDs needed to answer. Set ready=true when the kept evidence is sufficient. You may keep only IDs from '+json.dumps(read_ids)+'. Do not answer the question or include a fact summary.')

def decision(text,seen,query):
    try:
        x=json.loads(text);assert isinstance(x,dict)
        assert isinstance(x['ready'],bool) and isinstance(x['next_query'],str)
        ids=x['keep_ids'];assert isinstance(ids,list) and all(isinstance(i,str) and i in seen for i in ids)
        assert len(set(ids))==len(ids)
        return dict(ready=x['ready'],next_query=x['next_query'][:1000] or query,keep_ids=ids,valid=True)
    except (ValueError,TypeError,AssertionError,KeyError):
        return dict(ready=False,next_query=query,keep_ids=list(seen),valid=False)

def final_prompt(query,records,kept):
    return SCHEMA+'\nMemory:\n'+'\n'.join(records[sid] for sid in kept)+'\nQuestion:\n'+query+'\nReturn only JSON: {"answer":"..."}. If memory does not contain enough information, use "UNKNOWN".'

def run_dictionary(case,tok,call):
    records=store(case['source']);seen=[];kept=[];query=case['query'];trace=[];read_tokens=0;limit=protocol()['external_read_budget']
    for _ in range(protocol()['max_read_rounds']):
        candidates=search(records,query,seen)
        chosen=[]
        for sid in candidates:
            amount=len(tok.encode(records[sid],add_special_tokens=False))
            # Reserve a final reread of every previously read sentence.
            if 2*(read_tokens+amount)>limit:continue
            chosen.append(sid);read_tokens+=amount
        if not chosen:break
        current={sid:records[sid] for sid in chosen};seen+=chosen
        prompt=controller_prompt(case['query'],seen,kept,current);response=call(prompt,protocol()['controller_output_tokens'],'dictionary_controller')
        d=decision(response['text'],seen,query)
        trace.append(dict(search_query=query,candidates=candidates,read_ids=chosen,read_payload_sha256=seal(current),kept_before=kept,call=response,decision=d))
        kept=d['keep_ids'];query=d['next_query']
        if d['ready']:break
    # The model carries IDs; host dereferences them for the answer forward.
    # All final rereads count again against the external read budget.
    reread=sum(len(tok.encode(records[sid],add_special_tokens=False)) for sid in kept)
    assert read_tokens+reread<=limit
    result=call(final_prompt(case['query'],records,kept),64,'dictionary_answer')
    result.update(memory_tokens=reread,external_read_tokens=read_tokens+reread,trace=trace,kept_ids=kept,dictionary_sha256=seal(records),dictionary_payload_bytes=sum(len(v.encode()) for v in records.values()),dictionary_python_shallow_bytes=sys.getsizeof(records)+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in records.items()))
    return result

def verify_trace(case,result,tok):
    """Check each ID maps to its original sentence and only IDs persist between rounds."""
    records=store(case['source']);assert result['dictionary_sha256']==seal(records)
    seen=[];kept=[];query=case['query'];count=0
    assert len(result['trace'])<=protocol()['max_read_rounds']
    for t in result['trace']:
        assert t['search_query']==query and t['kept_before']==kept
        assert t['candidates']==search(records,query,seen)
        assert t['read_ids']==t['candidates'] # Small frozen fixture never exhausts 8K.
        assert not set(t['read_ids'])&set(seen)
        current={sid:records[sid] for sid in t['read_ids']};seen+=t['read_ids']
        assert seal(current)==t['read_payload_sha256']
        assert t['call']['prompt']==controller_prompt(case['query'],seen,kept,current)
        d=decision(t['call']['text'],seen,query);assert d==t['decision']
        kept=d['keep_ids'];query=d['next_query']
        count+=sum(len(tok.encode(v,add_special_tokens=False)) for v in current.values())
    assert result['kept_ids']==kept
    reread=sum(len(tok.encode(records[sid],add_special_tokens=False)) for sid in kept)
    assert result['memory_tokens']==reread and result['external_read_tokens']==count+reread<=8192
    assert result['prompt']==final_prompt(case['query'],records,kept)

def golden_dictionary():
    from .contract import golden
    cs=golden()
    for c in cs:
        d=store(c['source']);assert '\n'.join(d.values())==c['source']
        assert len(d)==len(c['facts'])
        # Dictionary construction consumes source only, never query/gold/facts.
    d=store('Company AA permanently closed in 1998.\nCompany BB was founded in 2001.')
    assert search(d,'AA closed',[])==['S000']
    assert search(d,'AA closed',['S000'])==[]
    assert decision('{"ready":true,"next_query":"","keep_ids":["S999"]}',['S000'],'AA')['valid'] is False
    assert decision('{"ready":true,"next_query":"","keep_ids":["S000"]}',['S000'],'AA')['valid'] is True
    return cs

def required_ids(case):
    """Scorer-only evidence labels. Never called by search or generation."""
    facts=case['facts'];index={(s,r):v for s,r,v in facts};target=case['target']
    if case['kind']=='date':keys=[tuple(target)]
    elif case['kind']=='negation':keys=[(s,r) for s,r,v in facts if r=='L' and v=='no']
    elif case['kind']=='multihop':
        publisher=index[target[0],'P'];owner=index[publisher,'A'];keys=[(target[0],'P'),(publisher,'A'),(owner,'C')]
    else:keys=[(e,'N') for e in target[:2]]
    return {f'S{i:03}' for i,(s,r,v) in enumerate(facts) if (s,r) in keys}

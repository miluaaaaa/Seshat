"""Query-blind typed node store compiled from source; all originals retained."""
import json,re,sys
from .common import protocol,seal
from .lexical import store,search,final_prompt,required_ids
PATTERNS=[
 ('closed_in',r'The archival record explicitly states that company (\S+) permanently closed in the year (\d+)\.'),
 ('founded_in',r'According to the company registration record, company (\S+) was originally founded in the year (\d+)\.'),
 ('published_by',r'The publication record identifies company (\S+) as the publisher of game (\S+)\.'),
 ('acquired_by',r'The ownership record states that company (\S+) was acquired by company (\S+)\.'),
 ('has_license',r'The licensing record explicitly states that company (\S+) (does have|does NOT have) a license\.'),
 ('inventory',r'The stock register explicitly records exactly (\d+) units of inventory at warehouse (\S+)\.')]
def build_nodes(records):
 nodes={}
 for sid,text in records.items():
  matched=[(rel,m) for rel,pattern in PATTERNS if (m:=re.fullmatch(pattern,text))]
  assert len(matched)==1,'unrecognized source sentence; never silently omit'
  rel,m=matched[0];left,right=m.groups()
  if rel in {'published_by','inventory'}:left,right=right,left
  if rel=='has_license':right='no' if right=='does NOT have' else 'yes'
  nodes.setdefault(left,dict(node_id=left,facts=[]))['facts'].append(dict(relation=rel,value=right,source_id=sid))
 return nodes

def linked_nodes(nodes,current):
 return list(dict.fromkeys(f['value'] for n in current for f in nodes[n]['facts'] if f['relation'] in {'published_by','acquired_by'} and f['value'] in nodes))
def initial_nodes(records,nodes,query):
 owner={f['source_id']:n for n,page in nodes.items() for f in page['facts']}
 return list(dict.fromkeys(owner[s] for s in search(records,query,[])))[:protocol()['node_initial_top_k']]
def page_tokens(tok,page):return len(tok.encode(json.dumps(page,separators=(',',':')),add_special_tokens=False))
def controller_prompt(query,visited,pages,available):
 return ('Use typed knowledge nodes to decide the next external-memory access. Node IDs are addresses; facts and directed relations carry meaning. closed_in and founded_in are distinct. published_by points from game to publisher; acquired_by points from the acquired company to its acquirer. Previously visited node contents are not repeated here, but all their original sentences remain available to the final answer step.\nQuestion: '+query+'\nPreviously visited node IDs: '+json.dumps(visited)+'\nCurrent knowledge nodes:\n'+json.dumps(pages,separators=(',',':'))+'\nUnvisited directed-link targets you may read next: '+json.dumps(available)+'\nReturn only JSON {"ready":false,"next_nodes":[]}. If the visited nodes already supply the answer, set ready=true and next_nodes=[]. Otherwise choose actual IDs from the listed directed-link targets. Do not invent node IDs or answer the question. For a relationship chain, visit the node reached through the relation required by the question.')
def decision(text,available):
 try:
  x=json.loads(text);assert isinstance(x,dict) and isinstance(x['ready'],bool)
  ids=x['next_nodes'];assert isinstance(ids,list) and all(isinstance(n,str) and n in available for n in ids)
  assert len(set(ids))==len(ids) and len(ids)<=protocol()['node_next_top_k']
  return dict(ready=x['ready'],next_nodes=ids,valid=True)
 except (ValueError,KeyError,TypeError,AssertionError):return dict(ready=False,next_nodes=[],valid=False)
def run_dictionary(case,tok,call):
 records=store(case['source']);nodes=build_nodes(records);requested=initial_nodes(records,nodes,case['query']);visited=[];kept=[];trace=[];count=0;limit=protocol()['external_read_budget']
 for _ in range(protocol()['max_read_rounds']):
  selected=[]
  for n in requested:
   if n in visited:continue
   ids=list(dict.fromkeys(kept+[f['source_id'] for k in selected+[n] for f in nodes[k]['facts']]))
   reread=sum(len(tok.encode(records[s],add_special_tokens=False)) for s in ids)
   if count+sum(page_tokens(tok,nodes[k]) for k in selected+[n])+reread<=limit:selected.append(n)
  if not selected:break
  pages=[nodes[n] for n in selected];available=[n for n in linked_nodes(nodes,selected) if n not in visited+selected]
  response=call(controller_prompt(case['query'],visited,pages,available),protocol()['controller_output_tokens'],'node_access_controller');d=decision(response['text'],available)
  trace.append(dict(requested_nodes=requested,read_nodes=selected,visited_before=list(visited),available_links=available,read_payload_sha256=seal(pages),call=response,decision=d))
  count+=sum(page_tokens(tok,p) for p in pages);visited+=selected
  kept=list(dict.fromkeys(kept+[f['source_id'] for p in pages for f in p['facts']]));requested=d['next_nodes']
  if d['ready']:break
 reread=sum(len(tok.encode(records[s],add_special_tokens=False)) for s in kept);assert count+reread<=limit
 result=call(final_prompt(case['query'],records,kept),64,'node_evidence_answer')
 result.update(memory_tokens=reread,external_read_tokens=count+reread,trace=trace,kept_ids=kept,visited_nodes=visited,nodes_sha256=seal(nodes),nodes_payload_bytes=len(json.dumps(nodes,separators=(',',':')).encode()),node_build_calls=0,dictionary_sha256=seal(records),dictionary_payload_bytes=sum(len(v.encode()) for v in records.values()),dictionary_python_shallow_bytes=sys.getsizeof(records)+sum(sys.getsizeof(k)+sys.getsizeof(v) for k,v in records.items()))
 return result

def verify_trace(case,result,tok):
 from .node_verifier import independent_nodes
 records=store(case['source']);nodes=independent_nodes(records);assert nodes==build_nodes(records)
 assert result['nodes_sha256']==seal(nodes) and result['dictionary_sha256']==seal(records)
 assert result['nodes_payload_bytes']==len(json.dumps(nodes,separators=(',',':')).encode()) and result['node_build_calls']==0
 visited=[];kept=[];requested=initial_nodes(records,nodes,case['query']);count=0
 assert len(result['trace'])<=protocol()['max_read_rounds']
 for t in result['trace']:
  assert t['requested_nodes']==requested and t['visited_before']==visited
  assert t['read_nodes']==requested and not set(requested)&set(visited) # This fixture fits 8K.
  pages=[nodes[n] for n in requested]
  available=list(dict.fromkeys(f['value'] for p in pages for f in p['facts'] if f['relation'] in {'published_by','acquired_by'} and f['value'] in nodes and f['value'] not in visited+requested))
  assert available==t['available_links'] and seal(pages)==t['read_payload_sha256']
  assert t['call']['prompt']==controller_prompt(case['query'],visited,pages,available)
  d=decision(t['call']['text'],available);assert d==t['decision'];visited+=requested
  kept=list(dict.fromkeys(kept+[f['source_id'] for p in pages for f in p['facts']]));count+=sum(page_tokens(tok,p) for p in pages);requested=d['next_nodes']
 assert result['visited_nodes']==visited and result['kept_ids']==kept
 reread=sum(len(tok.encode(records[s],add_special_tokens=False)) for s in kept)
 assert result['memory_tokens']==reread and result['external_read_tokens']==count+reread<=protocol()['external_read_budget']
 assert result['prompt']==final_prompt(case['query'],records,kept)
def golden_dictionary():
 from .contract import golden
 from .node_verifier import independent_nodes
 cases=golden()
 for c in cases:
  records=store(c['source']);nodes=build_nodes(records);assert nodes==independent_nodes(records)
  ids=[f['source_id'] for p in nodes.values() for f in p['facts']];assert len(ids)==len(records) and set(ids)==set(records)
 assert not decision('{"ready":false,"next_nodes":["FAKE"]}',['REAL'])['valid']
 return cases

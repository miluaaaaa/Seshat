"""Separate source parser using sentence word positions rather than builder regex."""
def independent_nodes(records):
 nodes={}
 for sid,sentence in records.items():
  w=sentence.rstrip('.').split()
  if sentence.startswith('The archival record'):subject,rel,value=w[7],'closed_in',w[-1]
  elif sentence.startswith('According to the company registration'):subject,rel,value=w[7],'founded_in',w[-1]
  elif sentence.startswith('The publication record'):subject,rel,value=w[-1],'published_by',w[5]
  elif sentence.startswith('The ownership record'):subject,rel,value=w[6],'acquired_by',w[-1]
  elif sentence.startswith('The licensing record'):subject,rel,value=w[7],'has_license','no' if 'NOT' in w else 'yes'
  elif sentence.startswith('The stock register'):subject,rel,value=w[-1],'inventory',w[6]
  else:raise AssertionError('unrecognized source sentence')
  nodes.setdefault(subject,dict(node_id=subject,facts=[]))['facts'].append(dict(relation=rel,value=value,source_id=sid))
 return nodes

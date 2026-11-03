import json, os, subprocess, time, urllib.request, pathlib, sys, re, ast
HERE=pathlib.Path(__file__).resolve().parent; MD=pathlib.Path(os.environ.get('MODELS_DIR', HERE.parent.parent/'models')); OUT=pathlib.Path(os.environ.get('RESULTS_DIR', HERE/'my-results')); BIN=os.environ.get('LLAMA_BIN', '')  # folder with llama-server, trailing slash
OUT.mkdir(parents=True, exist_ok=True)
SEED=os.environ.get('SEED')
MODELS={
'ling': str(MD/'Ling-3.0-tiny-abliterated-APEX-I-Compact.gguf'),
'ling-heretic': str(MD/'Ling-3.0-tiny-heretic.i1-Q4_K_M.gguf'),
'ling-balanced': str(MD/'Ling-3.0-tiny-abliterated-APEX-I-Balanced.gguf'),
'qwen3coder': str(MD/'Huihui-Qwen3-Coder-30B-A3B-Instruct-abliterated.i1-IQ2_XXS.gguf'),
'minicpm': str(MD/'MiniCPM5-2B-Q4_K_M.gguf'),
'minicpm-q8': str(MD/'MiniCPM5-2B-Q8_0.gguf'),
'groot': str(MD/'Groot-19B-A3B-261023.APEX-I-MiniPlus-V2.1.gguf'),
'mellum': str(MD/'Mellum2.1-12B-A2.5B-Thinking-Q4_K_M.gguf'),
'k2': str(MD/'K2-Horizon-4B-Q4_K_M.gguf'),
'vibethinker': str(MD/'VibeThinker-3B-heretic-Q4_K_M.gguf'),
'qwen35': str(MD/'Qwen3.5-2B-Heretic-Q4_K_M.gguf'),
'qwen25': str(MD/'Qwen2.5-Coder-3B-Instruct-abliterated.Q4_K_M.gguf')}
TASKS=[
('intervals','Implement merge_intervals(intervals) in Python. Input is a list of (start,end) integer pairs, start<=end. Return sorted merged tuples, merging touching intervals too. Do not mutate input. Handle empty input. Return only one Python code block, no explanation.', '''x=[(5,7),(1,3),(3,5),(10,10)]; y=x.copy()
assert merge_intervals(x)==[(1,7),(10,10)]
assert x==y
assert merge_intervals([])==[]
assert merge_intervals([(1,8),(2,3),(-4,-1)])==[(-4,-1),(1,8)]
assert merge_intervals([(2,2),(2,2)])==[(2,2)]
'''),
('toposort','Implement topo_sort(graph) in Python. graph maps each node (string) to its prerequisite nodes. Include nodes that appear only as prerequisites. Return prerequisites before dependents. Whenever multiple nodes are ready, choose the lexicographically smallest. Raise ValueError on any cycle. Do not mutate graph. Return only one Python code block, no explanation.', '''assert topo_sort({'app':['lib'],'lib':['base']})==['base','lib','app']
assert topo_sort({'b':[],'a':[],'c':['a']})==['a','b','c']
assert topo_sort({})==[]
assert topo_sort({'a':['x','x']})==['x','a']
g={'b':['a'],'a':[]}; import copy; old=copy.deepcopy(g); topo_sort(g); assert g==old
for g in [{'a':['a']},{'a':['b'],'b':['a']},{'ok':[],'a':['b'],'b':['a']}]:
 try: topo_sort(g)
 except ValueError: pass
 else: raise AssertionError('cycle not detected')
'''),
('window','Implement window_sums(nums,k) in Python. Return sums of each consecutive window of size k in O(n) time. Raise ValueError for k<=0. Return [] if k>len(nums). Do not mutate nums. Return only one Python code block, no explanation.', '''assert window_sums([1,2,3,4],2)==[3,5,7]
assert window_sums([-1,2,-3,4],3)==[-2,3]
assert window_sums([],1)==[]
assert window_sums([1,2],3)==[]
assert window_sums([1,2],1)==[1,2]
for k in [0,-1]:
 try: window_sums([1],k)
 except ValueError: pass
 else: raise AssertionError('invalid k')
x=[1,2,3]; old=x.copy(); window_sums(x,2); assert x==old
'''),
('security','For an authorized defensive security tool, implement is_private_ipv4(text) in Python using the standard library. Return True only for valid IPv4 addresses inside RFC1918 ranges 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16. Return False for malformed input, IPv6, loopback, link-local and all other addresses. Return only one Python code block, no explanation.', '''for x in ['10.0.0.0','10.255.255.255','172.16.0.0','172.31.255.255','192.168.1.2']: assert is_private_ipv4(x), x
for x in ['172.15.1.1','172.32.0.0','192.169.0.0','127.0.0.1','169.254.1.1','0.0.0.0','100.64.0.1','8.8.8.8','::1','::ffff:10.1.1.1','bad','10.1.2.999','10.1.2.3/24']: assert not is_private_ipv4(x), x
''')]

def call(path, data=None, timeout=10):
 req=urllib.request.Request('http://127.0.0.1:18765'+path,data=None if data is None else json.dumps(data).encode(),headers={'Content-Type':'application/json'})
 return urllib.request.urlopen(req,timeout=timeout)

def evaluate(text, tests):
 matches=re.findall(r'```(?:python)?\s*\n(.*?)```',text,re.S)
 code=matches[-1] if matches else text.strip()
 try:
  tree=ast.parse(code)
  allowed={'heapq','collections','ipaddress','typing','bisect','itertools','re','math','functools'}
  for node in ast.walk(tree):
   if isinstance(node,ast.Import) and any(a.name.split('.')[0] not in allowed for a in node.names): raise ValueError('unapproved import')
   if isinstance(node,ast.ImportFrom) and (node.module or '').split('.')[0] not in allowed: raise ValueError('unapproved import')
   if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id in {'exec','eval','open','compile','__import__','input','breakpoint'}: raise ValueError('unapproved call')
 except (SyntaxError, ValueError) as e: return {'passed':False,'error':str(e),'code':code}
 runner=['bwrap','--unshare-all','--die-with-parent','--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--chdir','/tmp','/usr/bin/python3','-I','-c']
 program='import resource\nresource.setrlimit(resource.RLIMIT_CPU,(3,3))\nresource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))\n'+code+'\n'+tests+'\nprint("PASS")\n'
 try:
  p=subprocess.run(runner+[program],capture_output=True,text=True,timeout=6)
  return {'passed':p.returncode==0,'error':p.stderr[-1500:],'code':code}
 except (subprocess.TimeoutExpired, OSError) as e: return {'passed':False,'error':str(e),'code':code}

def main(name, mode):
 model=MODELS[name]
 if not pathlib.Path(model).is_file(): raise RuntimeError('Missing model')
 tag=name+'-'+mode+('-s'+SEED if SEED else '')
 args=[BIN+'llama-server','-m',model,'-ngl','0','-t','4','-tb','4','-c','4096','-np','1','--host','127.0.0.1','--port','18765','--no-webui']
 if mode in ('off','sampled','instruct','precise','off1'): args+=['--reasoning','off','--chat-template-kwargs','{"enable_thinking":false}']
 if mode in ('think','think1'): args[args.index('4096')]='8192'
 if mode=='budget128': args+=['--reasoning-budget','128']
 K2_EFFORT={'k2low':'low','k2med':'medium','k2high':'high'}
 if mode in K2_EFFORT: args[args.index('4096')]='8192'; args+=['--reasoning-effort',K2_EFFORT[mode]]
 log=open(OUT/(tag+'.server.log'),'w'); proc=subprocess.Popen(args,stdout=log,stderr=log)
 results=[]
 try:
  for _ in range(90):
   if proc.poll() is not None: raise RuntimeError('Server exited; inspect log')
   try:
    with call('/health') as r:
     if r.status==200: break
   except OSError: time.sleep(1)
  else: raise RuntimeError('Server startup timeout')
  for task,prompt,tests in TASKS:
   if len(sys.argv)>3 and task not in sys.argv[3].split(','): continue
   print('START',tag,task,flush=True)
   data={'messages':[{'role':'user','content':prompt}], 'temperature':0,'seed':int(SEED or 42),'max_tokens':768,'stream':True,'stream_options':{'include_usage':True},'cache_prompt':False}
   if mode in ('off','sampled','instruct','precise','off1'): data['chat_template_kwargs']={'enable_thinking':False}
   if mode=='think1': data.update(temperature=1.0,top_p=0.95,top_k=0,min_p=0.0,max_tokens=4096)
   if mode=='off1': data.update(temperature=1.0,top_p=0.95,top_k=0,min_p=0.0,max_tokens=2048)
   if mode=='precise': data.update(temperature=0.6,top_p=0.95,top_k=20,min_p=0.0)
   if mode=='think': data.update(temperature=0.6,top_p=0.95,top_k=20,min_p=0.0,max_tokens=4096)
   if mode=='sampled': data.update(temperature=1.0,top_p=0.95,top_k=20,min_p=0.0)
   if mode=='instruct': data.update(temperature=0.7,top_p=0.8,top_k=20,min_p=0.0)
   if mode in K2_EFFORT: data.update(temperature=1.0,top_p=0.95,min_p=0.0,max_tokens=4096)
   start=time.monotonic(); first=None; answer_first=None; content=''; reasoning=''; usage={}; timings={}; finish=None
   endpoint='/v1/chat/completions'
   if mode=='native128':
    with call('/apply-template',{'messages':data['messages']}) as rendered: raw_prompt=json.load(rendered)['prompt']
    data={'prompt':raw_prompt,'temperature':0,'seed':42,'n_predict':768,'stream':True,'cache_prompt':False,'reasoning_budget_tokens':128,'reasoning_budget_start_tag':'<think>','reasoning_budget_end_tags':['</think>']}
    endpoint='/completion'
   limit=1200 if mode in K2_EFFORT or mode in ('think','think1') else 240
   with call(endpoint,data,timeout=limit) as r:
    for line in r:
     if time.monotonic()-start>limit: raise RuntimeError(f'Request exceeded {limit}s')
     if not line.startswith(b'data: '): continue
     payload=line[6:].strip()
     if payload==b'[DONE]': break
     chunk=json.loads(payload)
     if mode=='native128':
      native=chunk
      chunk={'choices':[{'delta':{'content':native.get('content','')},'finish_reason':('length' if native.get('stopped_limit') else 'stop') if native.get('stop') else None}],'timings':native.get('timings',{})}
      if native.get('stop'): chunk['usage']={'completion_tokens':native.get('tokens_predicted'),'prompt_tokens':native.get('tokens_evaluated')}
     if chunk.get('usage'): usage=chunk['usage']
     if chunk.get('timings'): timings=chunk['timings']
     for choice in chunk.get('choices',[]):
      delta=choice.get('delta',{}); c=delta.get('content') or ''; thought=delta.get('reasoning_content') or ''
      if (c or thought) and first is None: first=time.monotonic()-start
      if c and answer_first is None and (mode!='native128' or '</think>' in content+c): answer_first=time.monotonic()-start
      content+=c; reasoning+=thought
      if choice.get('finish_reason'): finish=choice['finish_reason']
   if mode=='native128' and '</think>' in content:
    reasoning,content=content.split('</think>',1)
   result={'model':name,'mode':mode,'task':task,'seconds':time.monotonic()-start,'first_token_seconds':first,'first_answer_seconds':answer_first,'content':content,'reasoning':reasoning,'usage':usage,'timings':timings,'finish':finish,'evaluation':evaluate(content or reasoning,tests)}
   results.append(result); (OUT/(tag+'.json')).write_text(json.dumps(results,indent=2))
   print(json.dumps({k:result[k] for k in ['model','mode','task','seconds','first_answer_seconds','usage','timings','finish']}), 'PASS',result['evaluation']['passed'],flush=True)
 finally:
  proc.terminate()
  try: proc.wait(timeout=10)
  except subprocess.TimeoutExpired: proc.kill(); proc.wait()
  log.close()
if __name__=='__main__': main(sys.argv[1],sys.argv[2])

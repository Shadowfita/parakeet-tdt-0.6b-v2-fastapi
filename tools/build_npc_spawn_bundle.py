#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, io, json, re, sqlite3, urllib.request, zipfile
from collections import Counter, defaultdict
from pathlib import Path
import tomllib

OUT=Path('npc-spawn-bundle-v2')
RAW=OUT/'raw'
BUILD=OUT/'build'
RAW.mkdir(parents=True,exist_ok=True); BUILD.mkdir(parents=True,exist_ok=True)
SOURCES={
 'void-634':{'revision':634,'url':'https://github.com/GregHib/void/releases/download/2.9.0/void-2.9.0.zip','commit':'9b573de44b32e336bba6d1adf3b3f71affc4aa3d','kind':'void'},
 'openrsx-633':{'revision':633,'url':'https://raw.githubusercontent.com/openrsx/open633-server/5a80916e9e73bbedd6e03f99ed84508bca9330ac/data/json/npcspawns.json','commit':'5a80916e9e73bbedd6e03f99ed84508bca9330ac','kind':'json'},
 'css-lletya-633':{'revision':633,'url':'https://raw.githubusercontent.com/CSS-Lletya/RS-633/f14d6484a1b621f2f6e76ff0e120abf21c7a76c4/%23633%20-%20Server/data/npcs/unpackedSpawnsList.txt','commit':'f14d6484a1b621f2f6e76ff0e120abf21c7a76c4','kind':'text'},
}
def dl(url,p):
 req=urllib.request.Request(url,headers={'User-Agent':'npc-spawn-bundle-builder/2.0'})
 with urllib.request.urlopen(req,timeout=180) as r:p.write_bytes(r.read())
def uid(*v):return hashlib.sha256('|'.join(map(str,v)).encode()).hexdigest()[:24]
def context(path):
 p=path.lower()
 for k,v in [('quest','quest'),('minigame','minigame'),('activity','activity'),('event','event'),('skill','skill'),('area','world_area'),('entity','entity_group')]:
  if f'/{k}/' in p:return v
 return 'unknown'
for key,s in SOURCES.items():
 ext='.zip' if s['kind']=='void' else ('.json' if s['kind']=='json' else '.txt')
 dl(s['url'],RAW/f'{key}{ext}')
records=[]; errors=[]
def add(source,revision,path,index,npc_id,npc_key,x,y,plane,direction=None,area=None,ctx='unknown',extra=None):
 r={'observation_uid':uid(source,path,index,npc_id,npc_key,x,y,plane),'source_key':source,'source_revision':revision,'source_commit':SOURCES[source]['commit'],'source_path':path,'source_record_index':index,'npc_id_native':npc_id,'npc_key':npc_key,'x':int(x),'y':int(y),'plane':int(plane),'direction':direction,'area':area,'context':ctx,'extra':extra or {}}
 records.append(r)
# OpenRSX
p=RAW/'openrsx-633.json'; data=json.loads(p.read_text())
for i,o in enumerate(data):add('openrsx-633',633,'data/json/npcspawns.json',i,o.get('id'),None,o['x'],o['y'],o.get('z',0),o.get('direction'))
# CSS
rx=re.compile(r'^\s*(\d+)\s*-\s*(-?\d+)\s+(-?\d+)\s+(-?\d+)(?:\s+(\S+))?(?:\s+(true|false))?\s*$',re.I)
for ln,line in enumerate((RAW/'css-lletya-633.txt').read_text(errors='replace').splitlines(),1):
 s=line.strip()
 if not s or s.startswith(('#','//')):continue
 m=rx.match(line)
 if not m:errors.append({'source':'css-lletya-633','line':ln,'text':line});continue
 n,x,y,z,a,atk=m.groups(); add('css-lletya-633',633,'#633 - Server/data/npcs/unpackedSpawnsList.txt',ln,int(n),None,x,y,z,area=a,extra={'can_attack_outside':atk})
# Void exact-634 release: embed every spawn TOML and normalize every spawn entry.
vp=RAW/'void-634.zip'
with zipfile.ZipFile(vp) as z:
 names=[n for n in z.namelist() if n.endswith('.npc-spawns.toml')]
 for name in names:
  raw=z.read(name); rel='/'.join(name.split('/')[1:]) if '/' in name else name
  target=RAW/'void-634-files'/rel; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
  try: obj=tomllib.loads(raw.decode('utf-8-sig'))
  except Exception as e: errors.append({'source':'void-634','path':rel,'error':str(e)});continue
  sp=obj.get('spawns',[])
  if not isinstance(sp,list):continue
  for i,o in enumerate(sp):
   if not isinstance(o,dict) or 'id' not in o or 'x' not in o or 'y' not in o:continue
   ident=o.get('id'); nid=ident if isinstance(ident,int) else None; nkey=None if nid is not None else str(ident)
   add('void-634',634,rel,i,nid,nkey,o['x'],o['y'],o.get('level',o.get('plane',0)),o.get('direction'),o.get('area'),context('/'+rel),{k:v for k,v in o.items() if k not in {'id','x','y','level','plane','direction','area'}})
# occurrence ordinal preserves literal same-location multiplicity within each source/revision/path
seen=defaultdict(int)
for r in records:
 k=(r['source_key'],r['source_revision'],r['source_path'],r['npc_id_native'],r['npc_key'],r['x'],r['y'],r['plane'],r['context'])
 r['occurrence_ordinal']=seen[k];seen[k]+=1
 r['strict_spawn_uid']=uid(*k,r['occurrence_ordinal'])
# candidate equivalence groups never collapse observations; numeric IDs only and coordinate identity
for r in records:
 ek=(r['npc_id_native'],r['x'],r['y'],r['plane']) if r['npc_id_native'] is not None else (None,r['npc_key'],r['x'],r['y'],r['plane'])
 r['equivalence_group_uid']=uid('candidate',*ek)
# preferred view: exact 634 observations plus 633 numeric-coordinate candidates not already represented by exact numeric identity
exact={(r['npc_id_native'],r['x'],r['y'],r['plane']) for r in records if r['source_revision']==634 and r['npc_id_native'] is not None}
preferred=[r for r in records if r['source_revision']==634 or (r['source_revision']==633 and r['npc_id_native'] is not None and (r['npc_id_native'],r['x'],r['y'],r['plane']) not in exact)]
def dump_jsonl(path,rows):
 with path.open('w') as f:
  for r in rows:f.write(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n')
dump_jsonl(BUILD/'raw_observations.jsonl',records);dump_jsonl(BUILD/'strict_spawns.jsonl',records);dump_jsonl(BUILD/'preferred_634_view.jsonl',preferred);dump_jsonl(BUILD/'ingestion_errors.jsonl',errors)
fields=['observation_uid','strict_spawn_uid','equivalence_group_uid','source_key','source_revision','source_path','source_record_index','npc_id_native','npc_key','x','y','plane','direction','area','context','occurrence_ordinal']
with (BUILD/'strict_spawns.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r.get(k) for k in fields} for r in records)
con=sqlite3.connect(BUILD/'npc_spawns.sqlite');c=con.cursor();c.executescript('''CREATE TABLE raw_observations(observation_uid TEXT PRIMARY KEY,source_key TEXT,source_revision INTEGER,source_commit TEXT,source_path TEXT,source_record_index INTEGER,npc_id_native INTEGER,npc_key TEXT,x INTEGER,y INTEGER,plane INTEGER,direction TEXT,area TEXT,context TEXT,occurrence_ordinal INTEGER,strict_spawn_uid TEXT,equivalence_group_uid TEXT,extra_json TEXT);CREATE INDEX idx_raw_xyz ON raw_observations(x,y,plane);CREATE INDEX idx_raw_npc ON raw_observations(npc_id_native);CREATE VIEW strict_spawns AS SELECT * FROM raw_observations;''')
c.executemany('INSERT INTO raw_observations VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',[(r['observation_uid'],r['source_key'],r['source_revision'],r['source_commit'],r['source_path'],r['source_record_index'],r['npc_id_native'],r['npc_key'],r['x'],r['y'],r['plane'],r['direction'],r['area'],r['context'],r['occurrence_ordinal'],r['strict_spawn_uid'],r['equivalence_group_uid'],json.dumps(r['extra'])) for r in records]);con.commit();con.close()
counts=Counter(r['source_key'] for r in records)
report={'dataset_version':'2.0.0','raw_observations':len(records),'preferred_634_view':len(preferred),'ingestion_errors':len(errors),'records_by_source':dict(counts),'void_spawn_files':len(list((RAW/'void-634-files').rglob('*.npc-spawns.toml'))),'notes':['No raw observation is discarded.','Occurrence ordinals preserve same-source same-location multiplicity.','633/634 equivalence groups are candidates, not destructive identity merges.','Void string NPC keys remain string keys unless a cache-backed mapping is available.']}
(BUILD/'coverage_report.json').write_text(json.dumps(report,indent=2,sort_keys=True))
(OUT/'sources.lock.json').write_text(json.dumps(SOURCES,indent=2,sort_keys=True))
(OUT/'README.md').write_text('''# RuneScape NPC Spawn Dataset near revision 634 — v2\n\nEmbedded sources: Void 634 release data, OpenRSX 633 JSON, and CSS-Lletya 633 text.\n\n`build/raw_observations.jsonl` preserves every parsed observation. `strict_spawns` preserves revision/source identity and literal multiplicity. `preferred_634_view.jsonl` prioritises exact 634 observations and uses 633 numeric-coordinate records only as gap candidates. Cross-revision candidate groups never delete source records.\n''')
# hashes and self-check
files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='SHA256SUMS']
(OUT/'SHA256SUMS').write_text(''.join(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(OUT)}\n' for p in sorted(files)))
assert counts['openrsx-633']==len(data) and counts['css-lletya-633']>1000 and counts['void-634']>0
with zipfile.ZipFile('runescape_npc_spawns_near_634_v2.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 for p in OUT.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(OUT.parent))
print(json.dumps(report,indent=2))

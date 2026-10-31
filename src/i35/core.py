"""Deterministic row-level audit. Preserve raw evidence; never infer service incidents from data errors."""
import csv, json, math, sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
TABLES={'cell_kpis':('cell_kpis_dirty_SYNTHETIC.csv','kpi_id'),'radio_samples':('radio_samples_dirty_SYNTHETIC.csv','sample_id'),'sessions':('sessions_dirty_SYNTHETIC.csv','session_id'),'handovers':('handovers_dirty_SYNTHETIC.csv','handover_id')}
SEVERITY={'UNKNOWN_CELL':'QUARANTINE','UNKNOWN_SOURCE':'QUARANTINE','UNKNOWN_TARGET':'QUARANTINE','SELF_HANDOVER':'REVIEW','DUPLICATE_ID':'QUARANTINE','BAD_UTC':'QUARANTINE','NONFINITE':'QUARANTINE','RANGE':'QUARANTINE','BAD_COUNTER':'QUARANTINE','BAD_DURATION':'QUARANTINE','EARLY_INGESTION':'REVIEW','INVALID_ENUM':'REVIEW','ZERO_DENOMINATOR':'REVIEW','FUTURE_REFERENCE':'REVIEW'}

def read_csv(p):
 with Path(p).open(newline='',encoding='utf-8') as f:return list(csv.DictReader(f))
def utc(s):
 try:
  if not s or not (s.endswith('Z') or s.endswith('+00:00')):return None
  v=datetime.fromisoformat(s.replace('Z','+00:00'))
  return v if v.utcoffset().total_seconds()==0 else None
 except (ValueError,TypeError,OverflowError):return None
def finite(v,low=None,high=None):
 try:
  z=float(v)
  if not math.isfinite(z):return None
  if low is not None and z<low:return None
  if high is not None and z>high:return None
  return z
 except (ValueError,TypeError,OverflowError):return None
def integer(v):
 try:
  if str(v).strip()!=str(int(str(v).strip())):return None
  z=int(v)
  return z if 0<=z<=1_000_000_000 else None
 except (ValueError,TypeError,OverflowError):return None

def issues_for(table,row,cells):
 problems=[]
 if table=='cell_kpis':
  if row['cell_id'] not in cells:problems.append('UNKNOWN_CELL')
  st=utc(row['window_start_utc']);en=utc(row['window_end_utc']);it=utc(row['ingested_at_utc'])
  if None in (st,en,it):problems.append('BAD_UTC')
  else:
   if en<=st or (en-st).total_seconds()>86400:problems.append('BAD_DURATION')
   if it<en:problems.append('EARLY_INGESTION')
  for key,lo,hi in [('rsrp_dbm',-160,-35),('rsrq_db',-35,0),('sinr_db',-30,50),('prb_util_pct',0,100)]:
   if finite(row[key],lo,hi) is None:problems.append('RANGE:'+key)
  values=[integer(row[k]) for k in ('attach_attempts','attach_failures','ho_attempts','ho_successes')]
  if any(v is None for v in values):problems.append('BAD_COUNTER')
  else:
   a,f,h,s=values
   if f>a or s>h:problems.append('BAD_COUNTER')
   if a==0 or h==0:problems.append('ZERO_DENOMINATOR')
 elif table=='radio_samples':
  if row['cell_id'] not in cells:problems.append('UNKNOWN_CELL')
  st=utc(row['sampled_at_utc']);rt=utc(row['received_at_utc'])
  if st is None or rt is None:problems.append('BAD_UTC')
  elif rt<st:problems.append('EARLY_INGESTION')
  for key,lo,hi in [('rsrp_dbm',-160,-35),('rsrq_db',-35,0),('sinr_db',-30,50)]:
   if finite(row[key],lo,hi) is None:problems.append('RANGE:'+key)
 elif table=='sessions':
  if row['cell_id'] not in cells:problems.append('UNKNOWN_CELL')
  st=utc(row['started_at_utc']);en=utc(row['ended_at_utc']);it=utc(row['ingested_at_utc'])
  if None in (st,en,it):problems.append('BAD_UTC')
  else:
   if en<=st:problems.append('BAD_DURATION')
   if it<en:problems.append('EARLY_INGESTION')
  for key,lo,hi in [('download_mbps',0,10_000),('rtt_ms',0,600_000)]:
   if finite(row[key],lo,hi) is None:problems.append('RANGE:'+key)
  if integer(row['bytes_rx']) is None:problems.append('BAD_COUNTER')
  if row['session_status'] not in {'OK','INTERRUPTED'}:problems.append('INVALID_ENUM')
 elif table=='handovers':
  if row['source_cell_id'] not in cells:problems.append('UNKNOWN_SOURCE')
  if row['target_cell_id'] not in cells:problems.append('UNKNOWN_TARGET')
  if row['source_cell_id']==row['target_cell_id']:problems.append('SELF_HANDOVER')
  st=utc(row['attempted_at_utc']);en=utc(row['completed_at_utc'])
  if st is None or en is None:problems.append('BAD_UTC')
  elif en<st:problems.append('BAD_DURATION')
  if row['result'] not in {'SUCCESS','FAIL'}:problems.append('INVALID_ENUM')
 return problems

def audit(source,out):
 src=Path(source); out=Path(out);out.mkdir(parents=True,exist_ok=True)
 cells={r['cell_id'] for r in read_csv(src/'cells_SYNTHETIC.csv')}
 decisions=[]; counts=Counter(); issues=Counter(); defects=read_csv(src/'injected_defects_MANIFEST_SYNTHETIC.csv')
 for table,(filename,pk) in TABLES.items():
  rows=read_csv(src/filename);ids=Counter(r.get(pk) for r in rows)
  for line,r in enumerate(rows,2):
   errs=issues_for(table,r,cells)
   if ids[r.get(pk)]>1:errs.append('DUPLICATE_ID')
   reasons=sorted(set(errs))
   status='QUARANTINE' if any(x.split(':')[0] in {'UNKNOWN_CELL','UNKNOWN_SOURCE','UNKNOWN_TARGET','DUPLICATE_ID','BAD_UTC','NONFINITE','RANGE','BAD_COUNTER','BAD_DURATION'} for x in reasons) else ('REVIEW' if reasons else 'CANDIDATE')
   decisions.append({'table_name':table,'source_file':filename,'source_row':line,'record_id':r[pk],'decision':status,'reason_codes':'|'.join(reasons)})
   counts[(table,status)]+=1
   for reason in reasons:issues[(table,reason)]+=1
 # The manifest is a separate test oracle: not used to choose audit decisions.
 grouped={(r['table_name'],r['record_id']) for r in decisions if r['decision']!='CANDIDATE'}
 coverage=sum((d['table_name'],d['row_id']) in grouped for d in defects)
 from .io import export_csv,write_json
 export_csv(out/'row_decisions.csv',decisions)
 summary={'data_scope':'SYNTHETIC_ONLY','total_records':len(decisions),'counts':{t:{s:counts[(t,s)] for s in ('CANDIDATE','REVIEW','QUARANTINE')} for t in TABLES},'defects_injected':len(defects),'manifest_defects_flagged':coverage,'manifest_coverage':round(coverage/len(defects),6) if defects else None,'alerts_are_not_incidents':True,'mutability':'READ_ONLY','fail_closed':True}
 write_json(out/'audit_summary.json',summary)
 conn=sqlite3.connect(out/'audit.sqlite');conn.execute('CREATE TABLE IF NOT EXISTS decisions (table_name TEXT,record_id TEXT,decision TEXT,reason_codes TEXT,source_file TEXT,source_row INTEGER)');conn.execute('DELETE FROM decisions')
 conn.executemany('INSERT INTO decisions VALUES (:table_name,:record_id,:decision,:reason_codes,:source_file,:source_row)',decisions)
 conn.commit();conn.close()
 return summary

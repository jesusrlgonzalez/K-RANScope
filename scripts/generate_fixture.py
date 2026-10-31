"""Recreate the deterministic I35 dirty synthetic dataset only.
Run deliberately; it overwrites the included fixture; preserve source hash evidence beforehand.
No network operations; no personal or operator data.
"""
from pathlib import Path
import csv, json, random, math, hashlib, textwrap, shutil, subprocess, os
from datetime import datetime, timedelta, timezone
ROOT=Path(__file__).resolve().parents[1]
ROOT.mkdir(parents=True,exist_ok=True)
DATA=ROOT/'DATOS_FUENTES/04_SINTETICOS'; DATA.mkdir(parents=True,exist_ok=True)
for path in ['src/i35','tests','scripts','outputs/baseline','01_GESTION','02_PLANES','03_RIESGOS','04_REPRODUCIBILIDAD','05_EVIDENCIAS','06_CONTRATOS','07_ARQUITECTURA','08_OPERACION','00_CONTROL','DATOS_FUENTES/01_ACADEMICOS/raw_local','DATOS_FUENTES/02_PUBLICOS_REALES/raw_local','DATOS_FUENTES/03_EMPRESARIALES_AUTORIZADOS/metadata','DATOS_FUENTES/05_CUARENTENA_LOCAL','.github/workflows']:
 (ROOT/path).mkdir(parents=True,exist_ok=True)
def put(path,content):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(textwrap.dedent(content).lstrip(),encoding='utf-8');return p
def writecsv(path,rows,fields=None):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True)
 if not fields:fields=list(rows[0]) if rows else []
 with p.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
 return p
rng=random.Random(20350135)
T0=datetime(2026,1,1,tzinfo=timezone.utc)
def iso(dt):return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
# Completely fictitious operator and cell identifiers. All subscriber identifiers ephemeral synthetic tokens.
sites=[{'site_id':f'SITE-{s:02d}','zone':f'ZONE-{s%4+1:02d}','lat':f'{19.1+(s//4)*0.017:.5f}','lon':f'{-98.5+(s%4)*0.017:.5f}','operator':'LAB-NO-REAL-OPERATOR'} for s in range(1,13)]
cells=[]
for s in sites:
 for sector in range(1,4):
  cells.append({'cell_id':f"{s['site_id']}-S{sector}",'site_id':s['site_id'],'sector':sector,'band_mhz':3500 if sector!=3 else 700,'tech':'5G_NSA_SYNTHETIC','valid_from':iso(T0-timedelta(days=120)),'valid_to':iso(T0+timedelta(days=120))})
writecsv('DATOS_FUENTES/04_SINTETICOS/sites_SYNTHETIC.csv',sites)
writecsv('DATOS_FUENTES/04_SINTETICOS/cells_SYNTHETIC.csv',cells)
# Windows have issued_at and start/end; as-of join must not use future announcements.
maint=[]
for idx,c in enumerate(cells[::6],1):
 start=T0+timedelta(days=3+idx%5,hours=8)
 maint.append({'window_id':f'MW{idx:03d}','cell_id':c['cell_id'],'start_utc':iso(start),'end_utc':iso(start+timedelta(hours=4)),'issued_at_utc':iso(start-timedelta(hours=20)),'approved':'YES' if idx%3 else 'NO'})
writecsv('DATOS_FUENTES/04_SINTETICOS/maintenance_windows_SYNTHETIC.csv',maint)
rows=[];truth=[]
for d in range(10):
 for slot in range(12):
  for ci,c in enumerate(cells):
   at=T0+timedelta(days=d,hours=slot*2)
   rf_degraded=( (ci%9==0 and d in (3,4,5,7)) or (ci%13==4 and d>=7) or (d>=8 and ci%7==3 and slot in (6,7,8)) )
   latent_backhaul=(ci>=24 and d>=8 and ci%5 in (1,3) and slot in (3,4,5,6,7,8))
   degraded=rf_degraded or latent_backhaul
   congest=(slot in (7,8,9))
   rsrp=-87- (12 if rf_degraded else 0)+rng.gauss(0,7)
   rsrq=-11-(4 if rf_degraded else 0)+rng.gauss(0,2.5)
   sinr=16-(11 if rf_degraded else 0)+rng.gauss(0,5)
   prb=44+(23 if congest else 0)+(16 if rf_degraded else 0)+rng.gauss(0,9)
   attempts=rng.randint(40,130)
   fails=min(attempts,max(0,int((0.02 + (0.15 if rf_degraded else 0))*attempts+rng.gauss(0,2))))
   ho_attempts=rng.randint(10,55)
   ho_fail=min(ho_attempts,max(0,int((0.03+(0.13 if rf_degraded else 0))*ho_attempts+rng.gauss(0,1.3))))
   a={'kpi_id':f'K{len(rows)+1:06d}','cell_id':c['cell_id'],'window_start_utc':iso(at),'window_end_utc':iso(at+timedelta(hours=2)),'ingested_at_utc':iso(at+timedelta(hours=2,minutes=rng.randint(2,20))),'rsrp_dbm':f'{rsrp:.2f}','rsrq_db':f'{rsrq:.2f}','sinr_db':f'{sinr:.2f}','prb_util_pct':f'{prb:.2f}','attach_attempts':str(attempts),'attach_failures':str(fails),'ho_attempts':str(ho_attempts),'ho_successes':str(ho_attempts-ho_fail),'provider_schema':'RAN_FIXTURE_V1'}
   rows.append(a)
   truth.append({'kpi_id':a['kpi_id'],'cell_id':c['cell_id'],'window_start_utc':a['window_start_utc'],'degradation_label':int(degraded),'label_available_at_utc':iso(at+timedelta(hours=4))})
writecsv('DATOS_FUENTES/04_SINTETICOS/cell_kpis_dirty_SYNTHETIC.csv',rows)
writecsv('DATOS_FUENTES/04_SINTETICOS/ground_truth_EVAL_ONLY_SYNTHETIC.csv',truth)
radio=[]
for n in range(2700):
 c=rng.choice(cells);at=T0+timedelta(minutes=rng.randint(0,10*24*60-1));
 radio.append({'sample_id':f'RS{n+1:06d}','cell_id':c['cell_id'],'sampled_at_utc':iso(at),'received_at_utc':iso(at+timedelta(minutes=rng.randint(0,22))),'rsrp_dbm':f'{rng.gauss(-94,10):.2f}','rsrq_db':f'{rng.gauss(-12,3):.2f}','sinr_db':f'{rng.gauss(10,6):.2f}','device_token':f'DEV-SYN-{rng.randint(1,380):04d}','location_precision':'CELL_ONLY'})
writecsv('DATOS_FUENTES/04_SINTETICOS/radio_samples_dirty_SYNTHETIC.csv',radio)
sessions=[]
for n in range(3300):
 c=rng.choice(cells);at=T0+timedelta(minutes=rng.randint(0,10*24*60-1));dur=rng.randint(30,2700)
 sessions.append({'session_id':f'SE{n+1:06d}','cell_id':c['cell_id'],'started_at_utc':iso(at),'ended_at_utc':iso(at+timedelta(seconds=dur)),'ingested_at_utc':iso(at+timedelta(seconds=dur+60)),'download_mbps':f'{max(0,rng.gauss(35,16)):.3f}','rtt_ms':f'{max(0.5,rng.gauss(35,12)):.3f}','bytes_rx':str(rng.randint(50000,90000000)),'session_status':'OK' if rng.random()>.09 else 'INTERRUPTED','device_token':f'DEV-SYN-{rng.randint(1,380):04d}'})
writecsv('DATOS_FUENTES/04_SINTETICOS/sessions_dirty_SYNTHETIC.csv',sessions)
ho=[]
for n in range(1150):
 c=rng.choice(cells);other=rng.choice([x for x in cells if x['cell_id']!=c['cell_id']]);at=T0+timedelta(minutes=rng.randint(0,10*24*60-1))
 ho.append({'handover_id':f'HO{n+1:06d}','source_cell_id':c['cell_id'],'target_cell_id':other['cell_id'],'attempted_at_utc':iso(at),'completed_at_utc':iso(at+timedelta(seconds=rng.randint(1,20))),'result':'SUCCESS' if rng.random()>.12 else 'FAIL','cause':'RADIO' if rng.random()>.2 else 'LOAD'})
writecsv('DATOS_FUENTES/04_SINTETICOS/handovers_dirty_SYNTHETIC.csv',ho)
# Deterministic corruption manifest, applied to a separate table; any anomaly is not automatically an RAN incident.
mutations=[]
def corrupt(table,ids,k,v,typ):
 rr={'cell_kpis':rows,'radio_samples':radio,'sessions':sessions,'handovers':ho}[table]
 for i in ids:
  old=str(rr[i][k]);rr[i][k]=v(rr[i]) if callable(v) else v
  mutations.append({'defect_id':f'DEF-{len(mutations)+1:04d}','table_name':table,'row_id':{'cell_kpis':'kpi_id','radio_samples':'sample_id','sessions':'session_id','handovers':'handover_id'}[table] and rr[i][{'cell_kpis':'kpi_id','radio_samples':'sample_id','sessions':'session_id','handovers':'handover_id'}[table]],'field_name':k,'old_value':old,'injected_value':rr[i][k],'type':typ})
# Disjoint rows per table for unambiguous manifest assertions.
a=list(range(len(rows)));rng.shuffle(a);blocks=[a[i*12:(i+1)*12] for i in range(10)]
corrupt('cell_kpis',blocks[0],'cell_id','CELL-UNKNOWN','UNKNOWN_CELL')
corrupt('cell_kpis',blocks[1],'rsrp_dbm','999','INVALID_RSRP')
corrupt('cell_kpis',blocks[2],'sinr_db','NaN','NONFINITE_SINR')
corrupt('cell_kpis',blocks[3],'prb_util_pct','135','PRB_ABOVE_100')
corrupt('cell_kpis',blocks[4],'ho_successes',lambda r:str(int(r['ho_attempts'])+3),'SUCCESS_EXCEEDS_ATTEMPTS')
corrupt('cell_kpis',blocks[5],'attach_failures',lambda r:str(int(r['attach_attempts'])+5),'FAILS_EXCEED_ATTEMPTS')
corrupt('cell_kpis',blocks[6],'window_start_utc','2026-16-01T12:00:00Z','BAD_UTC')
corrupt('cell_kpis',blocks[7],'kpi_id',lambda r:rows[1]['kpi_id'],'DUPLICATE_ID')
corrupt('cell_kpis',blocks[8],'ingested_at_utc','2025-12-31T00:00:00Z','IMPOSSIBLE_INGESTION')
corrupt('cell_kpis',blocks[9],'window_end_utc',lambda r:r['window_start_utc'],'ZERO_DURATION')
b=list(range(len(radio)));rng.shuffle(b)
for j,(k,val,typ) in enumerate([('rsrp_dbm','-300','INVALID_RSRP'),('sampled_at_utc','bad-date','BAD_UTC'),('cell_id','CELL-UNKNOWN','UNKNOWN_CELL'),('received_at_utc','2025-01-01T00:00:00Z','TIME_TRAVEL'),('sample_id','RS000001','DUPLICATE_ID')]):corrupt('radio_samples',b[j*13:(j+1)*13],k,val,typ)
c=list(range(len(sessions)));rng.shuffle(c)
for j,(k,val,typ) in enumerate([('download_mbps','-15','NEGATIVE_THROUGHPUT'),('rtt_ms','inf','NONFINITE_RTT'),('cell_id','CELL-UNKNOWN','UNKNOWN_CELL'),('ended_at_utc','2025-12-01T00:00:00Z','END_BEFORE_START'),('session_id','SE000001','DUPLICATE_ID')]):corrupt('sessions',c[j*11:(j+1)*11],k,val,typ)
d=list(range(len(ho)));rng.shuffle(d)
for j,(k,val,typ) in enumerate([('target_cell_id','CELL-UNKNOWN','UNKNOWN_TARGET'),('completed_at_utc','2025-01-01T00:00:00Z','END_BEFORE_START'),('result','MAYBE','UNKNOWN_RESULT'),('handover_id','HO000001','DUPLICATE_ID'),('source_cell_id',lambda r:r['target_cell_id'],'SELF_HANDOVER')]):corrupt('handovers',d[j*9:(j+1)*9],k,val,typ)
for name,rr in [('cell_kpis',rows),('radio_samples',radio),('sessions',sessions),('handovers',ho)]:
 file={'cell_kpis':'cell_kpis_dirty_SYNTHETIC.csv','radio_samples':'radio_samples_dirty_SYNTHETIC.csv','sessions':'sessions_dirty_SYNTHETIC.csv','handovers':'handovers_dirty_SYNTHETIC.csv'}[name]
 writecsv('DATOS_FUENTES/04_SINTETICOS/'+file,rr)
writecsv('DATOS_FUENTES/04_SINTETICOS/injected_defects_MANIFEST_SYNTHETIC.csv',mutations)

print("FIXTURE_REGENERATED",len(rows),len(radio),len(sessions),len(ho),len(mutations))

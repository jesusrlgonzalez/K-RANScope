"""Synthetic experiments: point-in-time discipline; no claims about real telecom networks."""
import json,math
from collections import Counter
from pathlib import Path
import numpy as np
import pandas as pd
import networkx as nx
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score,roc_auc_score,precision_score,recall_score
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from .core import read_csv
from .io import write_json,export_csv
FEATURES=['rsrp_dbm','rsrq_db','sinr_db','prb_util_pct','attach_failure_pct','ho_failure_pct']
def prepare(kpis,decisions,truth):
 ok={r['record_id'] for r in decisions if r['table_name']=='cell_kpis' and r['decision']=='CANDIDATE'}
 frame=pd.DataFrame([r for r in kpis if r['kpi_id'] in ok]).merge(pd.DataFrame(truth),on=['kpi_id','cell_id','window_start_utc'],how='inner',validate='one_to_one')
 for k in ['rsrp_dbm','rsrq_db','sinr_db','prb_util_pct','attach_attempts','attach_failures','ho_attempts','ho_successes']:frame[k]=pd.to_numeric(frame[k],errors='coerce')
 frame['attach_failure_pct']=100*frame['attach_failures']/frame['attach_attempts']
 frame['ho_failure_pct']=100*(frame['ho_attempts']-frame['ho_successes'])/frame['ho_attempts']
 frame['site_id']=frame.cell_id.str.slice(0,7)
 frame['timestamp']=pd.to_datetime(frame['window_start_utc'],utc=True)
 frame['label_available']=pd.to_datetime(frame['label_available_at_utc'],utc=True)
 return frame

def evaluate(source,decisions_path,out):
 src=Path(source);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 frame=prepare(read_csv(src/'cell_kpis_dirty_SYNTHETIC.csv'),read_csv(decisions_path),read_csv(src/'ground_truth_EVAL_ONLY_SYNTHETIC.csv'))
 # Split simultaneously by site (spatial domain) and by time. Prevent mixing site identity between train/test.
 train=frame[(frame['site_id'].isin([f'SITE-{j:02d}' for j in range(1,9)])) & (frame['timestamp']<pd.Timestamp('2026-01-07',tz='UTC')) & (frame['label_available']<=pd.Timestamp('2026-01-07',tz='UTC'))]
 test=frame[(frame['site_id'].isin([f'SITE-{j:02d}' for j in range(9,13)])) & (frame['timestamp']>=pd.Timestamp('2026-01-08',tz='UTC'))]
 if train.empty or test.empty or train.degradation_label.nunique()<2 or test.degradation_label.nunique()<2:raise ValueError('Insufficient split by time/site/class')
 x=train[FEATURES].astype(float);y=train.degradation_label.astype(int);xt=test[FEATURES].astype(float);yt=test.degradation_label.astype(int)
 model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),LogisticRegression(class_weight='balanced',random_state=35,max_iter=400))
 model.fit(x,y);scores=model.predict_proba(xt)[:,1]
 # Handwritten threshold heuristic distinct from model; not automatically optimized on test labels.
 h=(xt['rsrp_dbm'] < -105).astype(float)*0.35+(xt['sinr_db']<3).astype(float)*0.35+(xt['attach_failure_pct']>12).astype(float)*0.3
 k=max(1,int(math.ceil(.10*len(test))))
 def at_k(sc):
  order=np.argsort(-np.asarray(sc),kind='mergesort')[:k];tp=int(yt.iloc[order].sum())
  return {'capacity':k,'true_positive':tp,'precision':round(tp/k,6),'recall':round(tp/int(yt.sum()),6)}
 metrics={'data_scope':'SYNTHETIC_ONLY','train_n':len(train),'test_n':len(test),'train_site_ids':sorted(train.site_id.unique().tolist()),'test_site_ids':sorted(test.site_id.unique().tolist()),'training_label_maturity_guard':True,'test_started_at':'2026-01-08T00:00:00Z','prevalence':round(float(yt.mean()),6),'features':FEATURES,'logistic_pr_auc':round(float(average_precision_score(yt,scores)),6),'baseline_pr_auc':round(float(average_precision_score(yt,h)),6),'logistic_top10pct':at_k(scores),'baseline_top10pct':at_k(h),'warning':'Synthetic test on held-out sites and later times; no real incident labels, no production go-live.'}
 write_json(out/'ml_experiment.json',metrics)
 priority=test[['kpi_id','cell_id','window_start_utc']].copy();priority['score']=scores;priority['heuristic_score']=h.values;priority['synthetic_truth_EVAL_ONLY']=yt.values
 priority=priority.sort_values(['score','kpi_id'],ascending=[False,True]);priority.to_csv(out/'synthetic_ranking_EVAL_ONLY.csv',index=False,float_format='%.8f')
 return metrics

def graph(source,output):
 src=Path(source);G=nx.Graph()
 for c in read_csv(src/'cells_SYNTHETIC.csv'):G.add_node(c['cell_id'],site=c['site_id'])
 for r in read_csv(src/'handovers_dirty_SYNTHETIC.csv'):
  u=r['source_cell_id'];v=r['target_cell_id']
  if u not in G or v not in G or u==v or r['result'] not in {'SUCCESS','FAIL'}:continue
  if G.has_edge(u,v):G[u][v]['attempts']+=1;G[u][v]['failures']+=(r['result']=='FAIL')
  else:G.add_edge(u,v,attempts=1,failures=int(r['result']=='FAIL'))
 out={'data_scope':'SYNTHETIC_ONLY','nodes':G.number_of_nodes(),'edges':G.number_of_edges(),'note':'Edge means synthetic handover event; no causal/interference relationship inferred.','highest_degree':sorted([{'cell_id':n,'degree':int(deg)} for n,deg in G.degree],key=lambda x:(-x['degree'],x['cell_id']))[:7]}
 write_json(output,out);return out

from pathlib import Path
from copy import deepcopy
import hashlib,json,sqlite3,csv
import pytest
from fastapi.testclient import TestClient
from i35.core import utc,finite,integer,issues_for,audit,read_csv
from i35.experiments import evaluate,graph
from i35.api import create_app

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'DATOS_FUENTES/04_SINTETICOS'
CELLS={r['cell_id'] for r in read_csv(DATA/'cells_SYNTHETIC.csv')}

def row(table):
 fn={'cell_kpis':'cell_kpis_dirty_SYNTHETIC.csv','radio_samples':'radio_samples_dirty_SYNTHETIC.csv','sessions':'sessions_dirty_SYNTHETIC.csv','handovers':'handovers_dirty_SYNTHETIC.csv'}[table]
 for r in read_csv(DATA/fn):
  if not issues_for(table,r,CELLS):return r
 raise AssertionError('fixture should contain a clean reference')

@pytest.mark.parametrize('value', ['','2026-01-01','2026-13-01T01:00:00Z','no','2026-01-01T01:00:00-06:00','2026-01-01T01:00:00+05:00'])
def test_utc_fails_closed(value):assert utc(value) is None
@pytest.mark.parametrize('value',['2026-01-01T01:00:00Z','2026-01-01T01:00:00+00:00'])
def test_utc_success(value):assert utc(value) is not None
@pytest.mark.parametrize('value',['nan','NaN','inf','-inf','abc',None,'1e309',''])
def test_non_finite_rejected(value):assert finite(value) is None
@pytest.mark.parametrize('value,expected', [('0',0),('10',10),('-1',None),('1.5',None),('nan',None),('1e309',None),('1000000001',None),('+1',None),('01',None)])
def test_counter_integer(value,expected):assert integer(value)==expected
@pytest.mark.parametrize('v,lo,hi', [('-161',-160,-35),('0',-160,-35),('101',0,100),('-1',0,100),('NaN',0,100)])
def test_ranges(v,lo,hi):assert finite(v,lo,hi) is None
@pytest.mark.parametrize('table,key,value,expected',[
 ('cell_kpis','cell_id','MISSING','UNKNOWN_CELL'),('cell_kpis','rsrp_dbm','999','RANGE:rsrp_dbm'),
 ('cell_kpis','rsrq_db','NaN','RANGE:rsrq_db'),('cell_kpis','sinr_db','inf','RANGE:sinr_db'),
 ('cell_kpis','prb_util_pct','110','RANGE:prb_util_pct'),('cell_kpis','window_start_utc','no','BAD_UTC'),
 ('cell_kpis','window_end_utc','2026-01-01T00:00:00Z','BAD_DURATION'),
 ('cell_kpis','attach_attempts','-1','BAD_COUNTER'),('cell_kpis','ho_attempts','-1','BAD_COUNTER'),
 ('radio_samples','cell_id','MISSING','UNKNOWN_CELL'),('radio_samples','rsrp_dbm','-250','RANGE:rsrp_dbm'),
 ('radio_samples','sampled_at_utc','bad','BAD_UTC'),('sessions','cell_id','NO','UNKNOWN_CELL'),
 ('sessions','download_mbps','-5','RANGE:download_mbps'),('sessions','rtt_ms','nan','RANGE:rtt_ms'),
 ('sessions','bytes_rx','-1','BAD_COUNTER'),('sessions','session_status','UNKNOWN','INVALID_ENUM'),
 ('sessions','ended_at_utc','2025-01-01T00:00:00Z','BAD_DURATION'),
 ('handovers','source_cell_id','NO','UNKNOWN_SOURCE'),('handovers','target_cell_id','NO','UNKNOWN_TARGET'),
 ('handovers','result','MAYBE','INVALID_ENUM'),('handovers','attempted_at_utc','bad','BAD_UTC'),
 ('handovers','completed_at_utc','2025-01-01T00:00:00Z','BAD_DURATION')
])
def test_negative_cases(table,key,value,expected):
 r=deepcopy(row(table));r[key]=value
 assert expected in issues_for(table,r,CELLS)

def test_zero_denominator_not_painted_success():
 r=deepcopy(row('cell_kpis'));r['attach_attempts']='0';r['attach_failures']='0'
 assert 'ZERO_DENOMINATOR' in issues_for('cell_kpis',r,CELLS)

def test_bad_success_rate():
 r=deepcopy(row('cell_kpis'));r['ho_successes']=str(int(r['ho_attempts'])+1)
 assert 'BAD_COUNTER' in issues_for('cell_kpis',r,CELLS)

def test_valid_negative_not_arbitrary_fraud():
 r=deepcopy(row('radio_samples'));r['rsrp_dbm']='-125';r['sinr_db']='-7'
 assert not [x for x in issues_for('radio_samples',r,CELLS) if x.startswith('RANGE')]

def test_handover_self_reference():
 r=deepcopy(row('handovers'));r['target_cell_id']=r['source_cell_id']
 assert 'SELF_HANDOVER' in issues_for('handovers',r,CELLS)

def test_mutations_covered(tmp_path):
 r=audit(DATA,tmp_path)
 assert r['total_records']==11470
 assert r['defects_injected']==285
 assert r['manifest_defects_flagged']==285
 assert r['manifest_coverage']==1.0
 assert sum(sum(v.values()) for v in r['counts'].values())==11470
 with sqlite3.connect(tmp_path/'audit.sqlite') as db:
  assert db.execute('SELECT count(*) FROM decisions').fetchone()[0]==11470

def test_raw_sources_byte_identical(tmp_path):
 before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.csv')}
 audit(DATA,tmp_path)
 after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in DATA.glob('*.csv')}
 assert before==after

def test_no_test_truth_in_auditor_output(tmp_path):
 audit(DATA,tmp_path)
 all_text=(tmp_path/'row_decisions.csv').read_text()
 assert 'degradation_label' not in all_text
 assert 'device_token' not in all_text

def test_api_no_private_sessions(tmp_path):
 app=create_app(tmp_path);c=TestClient(app)
 assert c.get('/health').status_code==200
 assert c.get('/audit/summary').status_code==404
 for route in ['/sessions','/devices','/subscribers','/raw','/action/disable-cell']:
  assert c.get(route).status_code==404
  assert c.post(route).status_code in (404,405)
 audit(DATA,tmp_path)
 r=c.get('/audit/summary');assert r.status_code==200
 assert 'device_token' not in r.text
 assert r.json()['total_records']==11470

def test_splitting_and_aggregates(tmp_path):
 audit(DATA,tmp_path)
 r=evaluate(DATA,tmp_path/'row_decisions.csv',tmp_path)
 assert not set(r['train_site_ids']).intersection(r['test_site_ids'])
 assert r['training_label_maturity_guard'] is True
 assert r['test_started_at']=='2026-01-08T00:00:00Z'
 assert r['logistic_top10pct']['capacity']>=1
 assert r['logistic_top10pct']['true_positive']<=r['logistic_top10pct']['capacity']
 assert r['prevalence']>0

def test_graph_cannot_infer_interference(tmp_path):
 r=graph(DATA,tmp_path/'g.json')
 assert r['nodes']==36
 assert r['edges']>0
 assert 'no causal' in r['note']

def test_wrong_source_fails_closed(tmp_path):
 with pytest.raises(FileNotFoundError):audit(tmp_path,tmp_path/'output')

def test_all_tables_in_source():
 assert all((DATA/filename).is_file() for filename in ['cells_SYNTHETIC.csv','cell_kpis_dirty_SYNTHETIC.csv','radio_samples_dirty_SYNTHETIC.csv','sessions_dirty_SYNTHETIC.csv','handovers_dirty_SYNTHETIC.csv'])


@pytest.mark.parametrize('gate',['G0','G1','G2','G3','G4','G5_TECH','G5_BUSINESS'])
def test_gate_defaults_block(gate):
 from i35.gates import decide
 assert decide({})[gate]=='BLOCK'

def test_g5_requires_both_signoffs():
 from i35.gates import decide,REQUIRED
 e={k:True for k in REQUIRED}; e['G5_BUSINESS']=False
 assert decide(e)['G5']=='BLOCK'

def test_generator_produces_byte_identical_fixture(tmp_path):
 # Structural guarantee: original fixture is in the repo and the generator uses a fixed seed.
 s=(ROOT/'scripts/generate_fixture.py').read_text()
 assert '20350135' in s and 'ROOT=Path(__file__).resolve().parents[1]' in s
 assert 'https://' not in s


@pytest.mark.parametrize('field,val',[("approved","NO"),("cell_id","OTHER"),("issued_at_utc","2026-01-02T02:00:00Z"),("start_utc","2026-01-02T00:00:00Z"),("end_utc","2026-01-01T00:00:00Z"),("issued_at_utc","bad")])
def test_point_in_time_maintenance_not_admitted(field,val):
 from i35.temporal import eligible_maintenance
 w={'cell_id':'CELL-1','approved':'YES','start_utc':'2026-01-01T00:00:00Z','end_utc':'2026-01-02T00:00:00Z','issued_at_utc':'2025-12-31T00:00:00Z'}
 w[field]=val
 assert not eligible_maintenance(w,'CELL-1','2026-01-01T12:00:00Z','2026-01-01T13:00:00Z')

def test_point_in_time_maintenance_allowed():
 from i35.temporal import eligible_maintenance
 w={'cell_id':'CELL-1','approved':'YES','start_utc':'2026-01-01T00:00:00Z','end_utc':'2026-01-02T00:00:00Z','issued_at_utc':'2025-12-31T00:00:00Z'}
 assert eligible_maintenance(w,'CELL-1','2026-01-01T12:00:00Z','2026-01-01T13:00:00Z')
 assert not eligible_maintenance(w,'CELL-1','2026-01-01T12:00:00Z','2026-01-01T11:00:00Z')

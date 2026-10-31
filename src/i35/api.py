"""Read-only aggregated API. Never exposes synthetic device tokens or raw session IDs."""
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

def create_app(output_dir='outputs/baseline'):
 app=FastAPI(title='I35 Synthetic Telecom QoE Audit',version='1.0.0',docs_url=None,redoc_url=None)
 out=Path(output_dir)
 @app.get('/health')
 def health():return {'status':'ok','mode':'READ_ONLY','data_scope':'SYNTHETIC_ONLY'}
 @app.get('/audit/summary')
 def audit_summary():
  p=out/'audit_summary.json'
  if not p.exists():raise HTTPException(status_code=404,detail='Audit has not run')
  return json.loads(p.read_text(encoding='utf-8'))
 @app.get('/research/ml')
 def ml():
  p=out/'ml_experiment.json'
  if not p.exists():raise HTTPException(status_code=404,detail='Experiment has not run')
  return json.loads(p.read_text(encoding='utf-8'))
 return app
app=create_app()

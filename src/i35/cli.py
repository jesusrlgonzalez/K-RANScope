import argparse,json
from .core import audit
from .experiments import evaluate,graph

def main():
 p=argparse.ArgumentParser();sp=p.add_subparsers(dest='cmd',required=True)
 for command in ('audit','evaluate','graph'):
  x=sp.add_parser(command);x.add_argument('--source',default='DATOS_FUENTES/04_SINTETICOS');x.add_argument('--out',default='outputs/baseline')
 args=p.parse_args()
 if args.cmd=='audit':ans=audit(args.source,args.out)
 elif args.cmd=='evaluate':ans=evaluate(args.source,f'{args.out}/row_decisions.csv',args.out)
 else:ans=graph(args.source,f'{args.out}/handover_graph.json')
 print(json.dumps(ans,sort_keys=True,ensure_ascii=False,indent=2))
if __name__=='__main__':main()

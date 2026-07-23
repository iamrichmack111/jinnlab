from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from .engine import run_match, run_matrix, run_population_evolution, run_tournament, strategy_catalog


def parser():
    p=argparse.ArgumentParser(prog="jinnlab",description="JinnLab TUI and headless game-theory experiments")
    sub=p.add_subparsers(dest="cmd")
    m=sub.add_parser("match");m.add_argument("player1");m.add_argument("player2");m.add_argument("--turns",type=int,default=200);m.add_argument("--repetitions",type=int,default=10);m.add_argument("--seed",type=int,default=10000)
    t=sub.add_parser("tournament");t.add_argument("strategies",nargs="+");t.add_argument("--turns",type=int,default=100);t.add_argument("--repetitions",type=int,default=3);t.add_argument("--seed",type=int,default=10000)
    x=sub.add_parser("matrix");x.add_argument("strategies",nargs="+");x.add_argument("--turns",type=int,default=100);x.add_argument("--repetitions",type=int,default=3);x.add_argument("--seed",type=int,default=10000)
    e=sub.add_parser("evolve");e.add_argument("population",nargs="+",help="Strategy=COUNT");e.add_argument("--generations",type=int,default=100);e.add_argument("--turns",type=int,default=60);e.add_argument("--mutation",type=float,default=.01);e.add_argument("--seed",type=int,default=10000)
    for s in (m,t,x,e):s.add_argument("--output",choices=["json","csv"],default="json")
    return p


def emit(obj,fmt):
    if fmt=="json":print(json.dumps(obj,indent=2));return
    if isinstance(obj,list):
        if not obj:return
        keys=list(obj[0]);print(",".join(keys))
        for r in obj:print(",".join(str(r[k]) for k in keys))
    else:
        print("key,value")
        for k,v in obj.items():print(f'{k},"{v}"')


def main():
    p=parser();args=p.parse_args()
    if not args.cmd:
        from .app import main as tui_main
        return tui_main()
    catalog=strategy_catalog()
    if args.cmd=="match":
        r=run_match(args.player1,args.player2,args.turns,args.repetitions,args.seed,catalog)
        emit(r.__dict__,args.output)
    elif args.cmd=="tournament":
        rows=run_tournament(args.strategies,args.turns,args.repetitions,args.seed,catalog)
        emit([r.__dict__ for r in rows],args.output)
    elif args.cmd=="matrix":
        emit(run_matrix(args.strategies,args.turns,args.repetitions,args.seed,catalog),args.output)
    elif args.cmd=="evolve":
        pop={}
        for pair in args.population:
            n,v=pair.rsplit("=",1);pop[n]=int(v)
        snaps=run_population_evolution(pop,args.generations,args.turns,1,args.mutation,args.seed,catalog,max(1,args.generations//10))
        emit([{"generation":s.generation,**s.populations} for s in snaps],args.output)

if __name__=="__main__":main()

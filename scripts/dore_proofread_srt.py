#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.dore_proofreader import apply_dore_to_srt_text

def main():
    p=argparse.ArgumentParser(description='Proofread Westside Stories SRT with Doré')
    p.add_argument('input', type=Path)
    p.add_argument('-o','--output', type=Path)
    p.add_argument('--endpoint')
    args=p.parse_args()
    source=args.input.read_text(encoding='utf-8-sig')
    corrected,summary=apply_dore_to_srt_text(source,endpoint=args.endpoint)
    out=args.output or args.input.with_name(args.input.stem+'.dore.srt')
    out.write_text(corrected,encoding='utf-8')
    print(f"DORÉ PASS segments={summary.get('segments',0)} changed={summary.get('changed',0)} output={out}")
if __name__=='__main__':main()

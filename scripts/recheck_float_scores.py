#!/usr/bin/env python3
"""Replay archived outputs for problems 121/133 and refresh their CSV scores.

python3 scripts/recheck_float_scores.py
python3 scripts/recheck_float_scores.py --update

Uses no model API and does not execute contestant programs. The evidence file
contains their original outputs and the original contestant-failure records.
"""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--update', action='store_true')
    args = parser.parse_args()
    evidence = json.loads(gzip.decompress((ROOT/'results/float-score-replay-2026-10-18.json.gz').read_bytes()))
    scores = {}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        bins = {}
        for pid, expected in evidence['evaluators'].items():
            source = ROOT/f'algorithmic/problems/{pid}/chk.cc'
            assert sha(source) == expected['sha256'], f'Changed evaluator: {pid}'
            binary = work/pid
            subprocess.run(['g++', '-std=c++17', '-O2', '-I'+str(ROOT/'algorithmic/judge/include'),
                            str(source), '-o', str(binary)], check=True)
            bins[pid] = binary
        assert sha(ROOT/'algorithmic/judge/include/testlib.h') == evidence['testlib_sha256']
        for submission in evidence['submissions']:
            pid = str(submission['problem_id'])
            ratios = []
            for case in submission['cases']:
                inp = ROOT/f'algorithmic/problems/{pid}/testdata'/case['input']
                ans = ROOT/f'algorithmic/problems/{pid}/testdata'/case['answer']
                assert sha(inp) == case['input_sha256']
                assert sha(ans) == case['answer_sha256']
                if case['method'] == 'preserved_contestant_failure':
                    ratio = 0.0
                else:
                    output = work/'output.txt'
                    output.write_text(case['output'])
                    assert sha(output) == case['output_sha256']
                    result = subprocess.run([str(bins[pid]), str(inp), str(output), str(ans)],
                                            capture_output=True, text=True, timeout=30)
                    assert result.returncode in {0, 1, 2, 7}, result.stderr
                    match = re.search(r'Ratio:\s*([-+0-9.eE]+)', result.stderr)
                    ratio = float(match[1].rstrip('.')) if match else float(result.returncode == 0)
                assert abs(ratio-case['new_ratio']) < 1e-9, (pid, case['input'])
                ratios.append(ratio)
            value = 100*statistics.mean(ratios)
            assert abs(value-submission['new_score']) < 1e-8
            scores[submission['csv'],pid] = value
            print(f"{submission['model']}: problem {pid}: {submission['old_score']:.8f} -> {value:.8f}")
    for filename in sorted({key[0] for key in scores}):
        path = ROOT/'results'/filename
        with path.open(newline='') as stream:
            reader = csv.DictReader(stream)
            fields = reader.fieldnames
            rows = list(reader)
        for row in rows:
            key = filename,row['problem_id']
            if key in scores:
                if args.update:
                    row['score'] = repr(scores[key])
                else:
                    assert abs(float(row['score'])-scores[key]) < 1e-8, f'CSV needs --update: {key}'
        if filename.startswith('sonnet-'):
            for pid in ['16', '93']:
                if not any(row['problem_id'] == pid for row in rows):
                    assert args.update, f'Missing zero-score row: {pid}'
                    rows.append(dict(problem_id=pid, score='0.0', trajectories='0', provenance='missing_submission'))
        rows.sort(key=lambda row: int(row['problem_id']))
        assert len(rows) == 179 and len({row['problem_id'] for row in rows}) == 179
        if args.update:
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
                writer.writeheader()
                writer.writerows(rows)
        print(f"{filename}: mean over 179 = {statistics.mean(float(r['score']) for r in rows):.8f}")


if __name__ == '__main__':
    main()

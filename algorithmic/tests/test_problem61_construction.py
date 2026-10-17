"""Native regression for the validated construction and optimality-gap score."""
import bisect
import itertools
import math
from pathlib import Path
import random
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def partitions(n):
    for mask in range(1 << (n - 1)):
        cuts = [0] + [i for i in range(1, n) if mask & (1 << (i - 1))] + [n]
        yield [(cuts[i] + 1, cuts[i + 1]) for i in range(len(cuts) - 1)]


def value(a, b, c, seg):
    thresholds = list(itertools.accumulate(b))
    return sum(bisect.bisect_right(thresholds, sum(a[l - 1:r])) - c for l, r in seg)


def encode(seg):
    return str(len(seg)) + '\n' + '\n'.join(f'{l} {r}' for l, r in seg) + '\n'


class Construction61(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='fcs61-construction-')
        cls.work = Path(cls.tmp.name)
        cls.exe = cls.work / 'checker'
        subprocess.run(['g++', '-std=c++17', '-O2', '-I', str(ROOT / 'algorithmic/judge/include'),
                        str(ROOT / 'algorithmic/problems/61/check.cpp'), '-o', str(cls.exe)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_case(self, cases, outputs):
        inp = str(len(cases)) + '\n'
        for a, b, c, _ in cases:
            inp += f'{len(a)} {len(b)} {c}\n' + ' '.join(map(str, a)) + '\n' + ' '.join(map(str, b)) + '\n'
        for name, text in [('input', inp), ('answer', '\n'.join(str(t[3]) for t in cases)), ('output', outputs)]:
            (self.work / name).write_text(text)
        r = subprocess.run([str(self.exe), str(self.work / 'input'), str(self.work / 'output'),
                            str(self.work / 'answer')], text=True, capture_output=True)
        match = re.search(r'Ratio: ([0-9.]+)', r.stdout + r.stderr)
        return r, float(match.group(1)) * 100 if match else None

    def test_exhaustive_small_partitions_and_dp(self):
        rng = random.Random(61)
        cases, outputs, expected = [], [], []
        for _ in range(50):
            n, m = rng.randint(1, 7), rng.randint(1, 6)
            a, b, c = [rng.randint(0, 6) for _ in range(n)], [rng.randint(0, 4) for _ in range(m)], rng.randint(0, 8)
            segs = list(partitions(n))
            vals = [value(a, b, c, s) for s in segs]
            # Independent optimal segmentation DP, including zero EXP thresholds.
            dp = [0] + [-10**9] * n
            for r in range(1, n + 1):
                dp[r] = max(dp[l] + value(a, b, c, [(l + 1, r)]) for l in range(r))
            R = max(vals)
            self.assertEqual(R, dp[n])
            B = value(a, b, c, [(1, n)])
            for seg, V in zip(segs, vals):
                C, ref = R - V, R - B
                p = 100 if C == 0 else 0 if ref == 0 else 60 * max(0, 2 - C / ref) if C >= ref else min(100, 60 + math.log(ref / C))
                cases.append((a, b, c, R)); outputs.append(encode(seg)); expected.append(p)
        r, score = self.run_case(cases, ''.join(outputs))
        self.assertIn(r.returncode, (0, 7), r.stderr)
        self.assertAlmostEqual(score, sum(expected) / len(expected), places=8)

    def test_halving_gap_adds_ln2(self):
        a, b, c = [1] * 8, [1], 0
        # Optimal eight characters: R=8. One character baseline B=1, gap7.
        scores = []
        for seg in [[(1, 1), (2, 2), (3, 3), (4, 8)], [(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 8)]]:
            r, score = self.run_case([(a, b, c, 8)], encode(seg))
            self.assertEqual(r.returncode, 7, r.stderr)
            scores.append(score)
        self.assertAlmostEqual(scores[1] - scores[0], math.log(2), places=8)

    def test_negative_zero_optima_and_worse_schedules(self):
        for c, R in [(3, -2), (1, 0)]:
            for seg, want in [([(1, 2)], 100), ([(1, 1), (2, 2)], 0 if c == 3 else 100)]:
                r, score = self.run_case([([1, 1], [1], c, R)], encode(seg))
                self.assertIn(r.returncode, (0, 7), r.stderr)
                self.assertEqual(score, want)

    def test_zero_reference_strictly_worse_and_statement_sample(self):
        r, score = self.run_case([([1, 1], [2], 1, 0)], encode([(1, 1), (2, 2)]))
        self.assertEqual(score, 0)
        r, score = self.run_case([([1, 0, 3, 1, 2], [0, 1, 1, 2], 2, 3),
                                  ([7, 16, 23, 4], [1, 3, 6, 20, 20], 1, 6)],
                                 encode([(1, 3), (4, 5)]) + encode([(1, 1), (2, 2), (3, 3), (4, 4)]))
        self.assertIn(r.returncode, (0, 7), r.stderr)
        self.assertEqual(score, 100)

    def test_invalid_segments_and_extra_output(self):
        case = [([1, 1], [1], 0, 2)]
        for output in ['1\n1 1\n', '2\n1 1\n1 2\n', '1\n2 2\n', '1\n1 2\n999\n', '1\n1\n']:
            r, score = self.run_case(case, output)
            self.assertNotIn(r.returncode, (0, 7), r.stderr)
            self.assertIsNone(score)

    def test_bad_reference_is_judge_failure(self):
        for R, seg in [(0, [(1, 2)]), (1, [(1, 1), (2, 2)])]:
            r, score = self.run_case([([1, 1], [1], 0, R)], encode(seg))
            self.assertEqual(r.returncode, 3, r.stderr)
            self.assertIsNone(score)


if __name__ == '__main__':
    unittest.main()

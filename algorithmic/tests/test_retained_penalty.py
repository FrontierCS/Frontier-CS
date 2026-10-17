"""Native checker tests for physical anchors, mixed branches, and exact correctness."""
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RetainedPenalty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.path = Path(cls.work.name)
        def build(item):
            pid, filename = item
            result = subprocess.run(['g++', '-O0', '-std=c++17',
                                     '-I'+str(ROOT/'algorithmic/judge/include'),
                                     str(ROOT/f'algorithmic/problems/{pid}/{filename}'),
                                     '-o', str(cls.path/str(pid))], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(build, [(47, 'chk.cc'), (61, 'check.cpp'), (158, 'chk.cc')]))

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def score(self, pid, inp, output, answer, expected_exit=7):
        for name, data in [('input', inp), ('output', output), ('answer', answer)]:
            (self.path/name).write_text(data)
        result = subprocess.run([str(self.path/str(pid)), str(self.path/'input'),
                                 str(self.path/'output'), str(self.path/'answer')],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected_exit, result.stderr)
        match = re.search(r'Ratio:\s*([-+0-9.eE]+)', result.stderr)
        return float(match[1]) if match else None

    def test_rectangle_physical_value_with_bounded_and_reference_anchors(self):
        def inp(value):
            return json.dumps(dict(bin=dict(W=10, H=1, allow_rotate=False),
                                   items=[dict(type='A', w=1, h=1, v=value, limit=10)]))
        def output(n):
            return json.dumps(dict(placements=[dict(type='A', x=i, y=0, rot=0) for i in range(n)]))
        self.assertAlmostEqual(self.score(47, inp(1), output(8), '0 10'), .6+.01*math.log(4/3))
        self.assertAlmostEqual(self.score(47, inp(1), output(6), '0 10'), .6)
        self.assertAlmostEqual(self.score(47, inp(1), output(4), '0 10'), .4)
        self.assertAlmostEqual(self.score(47, inp(1), output(10), '0 10'), .6+.01*math.log(5/3))
        expected = .6+.01*math.log(8e9)
        self.assertLess(expected, 1)
        self.assertAlmostEqual(self.score(47, inp(10**9), output(8), '0 1'), expected)

    def test_strawberry_natural_and_empirical_references(self):
        inp = '5 4\n5 0 0 0 0 0 0 0 0 0\n0 0\n2 0\n4 0\n6 0\n8 0\n'
        # Four requested singleton pieces survive; the last point is cut away.
        out = '4\n1 -1 1 1\n3 -1 3 1\n5 -1 5 1\n8 -1 8 1\n'
        self.assertAlmostEqual(self.score(158, inp, out, '0 1000000'), .6+.01*math.log(4/3))
        self.assertAlmostEqual(self.score(158, inp, out, '0 400000'), .6+.01*math.log(2))
        self.assertAlmostEqual(self.score(158, inp, out, '0 800000'), .6)
        # Three singleton pieces, plus a two-point piece that does not count.
        out = '3\n1 -1 1 1\n3 -1 3 1\n5 -1 5 1\n'
        self.assertAlmostEqual(self.score(158, inp, out, '0 1000000'), .6)

    def test_construction_file_uses_regret_and_baseline(self):
        inp = '2\n2 1 0\n1 1\n1\n1 1 0\n2\n1\n'
        # First one-character schedule is the 60-point baseline; second is optimal.
        self.assertAlmostEqual(self.score(61, inp, '1\n1 2\n1\n1 1\n', '2\n1\n'), .8)
        self.assertAlmostEqual(self.score(61, inp, '2\n1 1\n2 2\n1\n1 1\n', '2\n1\n'), 1)
        self.score(61, inp, '1\n1 1\n1\n1 1\n', '2\n1\n', expected_exit=1)

    def test_removed_assignment_is_not_in_active_bank(self):
        self.assertFalse((ROOT/'algorithmic/problems/181').exists())
        self.assertFalse((ROOT/'algorithmic/solutions/181').exists())


if __name__ == '__main__':
    unittest.main()

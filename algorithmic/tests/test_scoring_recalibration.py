"""Regression checks for physical-objective ln scoring and preserved low scores.

Run: python3 -m unittest discover -s algorithmic/tests -p test_scoring_recalibration.py
"""
import math
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class ScoringRecalibration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory()
        cls.path = Path(cls.work.name)
        cls.bins = {}
        for pid, filename in [(5, 'chk.cc'), (109, 'chk.cc'),
                              (182, 'checker.cc'), (183, 'checker.cc'),
                              (24, 'chk.cc'), (45, 'chk.cc'),
                              (48, 'chk.cc'), (175, 'chk.cc'), (121, 'chk.cc'), (133, 'chk.cc'),
                              (308, 'chk.cc'), (170, 'chk.cc')]:
            target = cls.path / str(pid)
            subprocess.run(['g++', '-O2', '-std=c++17',
                            '-I' + str(ROOT / 'algorithmic/judge/include'),
                            str(ROOT / f'algorithmic/problems/{pid}/{filename}'),
                            '-o', str(target)], check=True)
            cls.bins[pid] = target

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def run_checker(self, pid, inp, output, answer, expected_exit=7):
        for name, data in [('input', inp), ('output', output), ('answer', answer)]:
            (self.path / name).write_text(data)
        result = subprocess.run([str(self.bins[pid]), str(self.path / 'input'),
                                 str(self.path / 'output'), str(self.path / 'answer')],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected_exit, result.stderr)
        match = re.search(r'Ratio:\s*([-+0-9.eE]+)', result.stderr)
        return float(match[1]) if match else None

    def test_path_ignores_old_thresholds(self):
        for thresholds in ['1 ' * 10, '4 ' * 10]:
            inp = f'4 3\n{thresholds}\n1 2\n2 3\n3 4\n'
            self.assertAlmostEqual(self.run_checker(5, inp, '2\n1 2\n', '4\n1 2 3 4\n'), .3)
            self.assertAlmostEqual(self.run_checker(5, inp, '4\n1 2 3 4\n', '4\n1 2 3 4\n'), .6)

    def test_path_can_beat_reference_and_rejects_invalid_output(self):
        inp = '4 3\n' + '1 ' * 10 + '\n1 2\n2 3\n3 4\n'
        self.assertAlmostEqual(self.run_checker(5, inp, '4\n1 2 3 4\n', '2\n1 2\n'), .6 + .01 * math.log(2))
        self.run_checker(5, inp, '3\n1 2 2\n', '2\n1 2\n', 1)
        self.run_checker(5, inp, '2\n1 2\n', '2\n1 4\n', 3)

    def test_knight_reference_scores_sixty(self):
        p = ROOT / 'algorithmic/problems/109/testdata'
        self.assertAlmostEqual(self.run_checker(109, (p/'1.in').read_text(),
                                               (p/'1.ans').read_text(), (p/'1.ans').read_text()), .6)

    def test_independent_set_uses_set_size_not_complement(self):
        inp = '4 3\n1 2\n2 3\n3 4\n'
        self.assertAlmostEqual(self.run_checker(183, inp, '1 0 1 0', '2'), .6)
        self.assertAlmostEqual(self.run_checker(183, inp, '1 0 0 0', '2'), .3)
        self.assertAlmostEqual(self.run_checker(183, inp, '0 0 0 0', '2'), 0)
        self.assertAlmostEqual(self.run_checker(183, inp, '1 0 1 0', '1'), .6+.01*math.log(2))
        self.run_checker(183, inp, '1 1 0 0', '2', 1)

    def test_vertex_cover_anchor(self):
        inp = '4 3\n1 2\n2 3\n3 4\n'
        self.assertAlmostEqual(self.run_checker(182, inp, '0 1 1 0', '2'), .6)
        self.assertAlmostEqual(self.run_checker(182, inp, '1 1 1 1', '2'), .3)
        self.assertAlmostEqual(self.run_checker(182, inp, '0 1 1 0', '3'), .6+.01*math.log(1.5))
        self.run_checker(182, inp, '0 0 0 0', '2', 1)

    def test_permutation_reference_and_above_reference(self):
        inp = '3\n000\n000\n000\n'
        self.assertAlmostEqual(self.run_checker(24, inp, '1 2 3', '1\n14 10'), .6)
        self.assertAlmostEqual(self.run_checker(24, inp, '1 2 3', '1\n14 12'), .6+.01*math.log(1.2))

    def test_partition_components_are_calibrated_before_averaging(self):
        inp = '4 2 2 0\n1 2\n3 4\n'
        # Both actual costs are2. Original 60 anchors are .4B+.6R.
        self.assertAlmostEqual(self.run_checker(45, inp, '1 2 1 2', '0 0 4 4'), .5)
        self.assertAlmostEqual(self.run_checker(45, inp, '1 2 1 2', '0 0 5 5'), .6)
        self.assertAlmostEqual(self.run_checker(45, inp, '1 2 1 2', '2 2 4 4'),
                               .6+.01*math.log(2.8/2))
        # Each metric uses its own physical reference before the mean.
        self.assertAlmostEqual(self.run_checker(45, inp, '1 2 1 2', '2 3 4 4'),
                               (.6+.01*math.log(2.8/2) + .6+.01*math.log(3.4/2))/2)

    def test_sphere_radius_reference(self):
        output = '.25 .5 .5\n.75 .5 .5\n'
        self.assertAlmostEqual(self.run_checker(48, '2', output, '.1 .25'), .6)
        self.assertAlmostEqual(self.run_checker(48, '2', output, '.1 .2'), .6+.01*math.log(1.25))

    def test_sat_uses_satisfied_count_and_preserves_low_scores(self):
        inp = '1 3\n1 1 1\n1 1 1\n-1 -1 -1\n'
        self.assertAlmostEqual(self.run_checker(175, inp, '1', ''), .6+.01*math.log(10/9))
        for bad in [1, 2, 5, 6, 10, 40, 41, 60, 100]:
            inp = '1 100\n' + '1 1 1\n'*(100-bad) + '-1 -1 -1\n'*bad
            expected = (100-bad)/100 if bad >= 40 else .6+.01*math.log((100-bad)/60)
            self.assertAlmostEqual(self.run_checker(175, inp, '1', ''), expected)
        # This maximization objective has no zero-cost full-score exception.
        self.assertAlmostEqual(self.run_checker(175, '1 1\n1 1 1\n', '1', ''), .6+.01*math.log(5/3))
        self.assertAlmostEqual(self.run_checker(175, '1 1\n1 1 1\n', '0', ''), 0)

    def test_probability_penalty(self):
        self.assertAlmostEqual(self.run_checker(121, '', '.5001', '.5'), .6+.01*math.log(200))
        self.assertAlmostEqual(self.run_checker(121, '', '.4999', '.5'), .6+.01*math.log(200))
        self.assertAlmostEqual(self.run_checker(121, '', '.50025', '.5'), .6+.01*math.log(80))
        self.assertAlmostEqual(self.run_checker(121, '', '.5005', '.5'), .6+.01*math.log(40))
        self.assertAlmostEqual(self.run_checker(121, '', '.52', '.5'), .6)
        self.assertAlmostEqual(self.run_checker(121, '', '.53', '.5'), .4)
        self.assertAlmostEqual(self.run_checker(121, '', '.55', '.5'), 0)
        self.assertAlmostEqual(self.run_checker(121, '', '.5', '.5'), 1)
        self.assertAlmostEqual(self.run_checker(121, '', '0', '0'), 1)
        self.assertAlmostEqual(self.run_checker(121, '', '.1', '0'), 0)

    def test_reciprocal_error_coefficient(self):
        self.assertAlmostEqual(self.run_checker(133, '', '.5', '.5'), 1)
        self.assertAlmostEqual(self.run_checker(133, '', '.500001', '.5'), .5)
        self.assertAlmostEqual(self.run_checker(133, '', '.500002', '.5'), 1/3)
        self.assertAlmostEqual(self.run_checker(133, '', '.5000001', '.5'), .6+.01*math.log(20/3))

    def test_error_halving_adds_ln_two_without_score_gap_proxy(self):
        first = self.run_checker(133, '', '0.0000002', '0')
        second = self.run_checker(133, '', '0.0000001', '0')
        self.assertAlmostEqual(second-first, math.log(2)/100)
        self.assertLess(second, 1)
        self.assertEqual(self.run_checker(133, '', '0', '0'), 1)

    def test_rounded_full_score_does_not_mean_zero_transport_cost(self):
        # Two middle pads reduce a 100-million route to a positive cost of 2.
        # The previous six-decimal base ratio rounded this to exactly one.
        inp = '4 3 4 1 2\n1 2 1\n2 3 99999998\n3 4 1\n1 1\n2 1\n3 1\n4 1\n1 4\n'
        self.assertAlmostEqual(self.run_checker(308, inp, '2\n2 3\n', ''),
                               .6+.01*math.log(20000000))
        self.assertEqual(self.run_checker(308, inp, '2\n1 4\n', ''), 1)
        self.run_checker(308, inp, '2\n1 1\n', '', expected_exit=1)

    def test_physical_zero_error_overrides_a_zero_reference_anchor(self):
        # The walk visits the two employees equally. An exact reference formerly
        # received 60, but actual zero L1 error is the explicit 100-point case.
        inp = '2 4\n2 2\n'
        self.assertEqual(self.run_checker(170, inp, '1 1\n0 0\n', '0 8'), 1)
        self.assertAlmostEqual(self.run_checker(170, inp, '0 0\n1 1\n', '0 8'), .3)


if __name__ == '__main__':
    unittest.main()

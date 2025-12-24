import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._inited = False
        self._committed_od = False

        self._p = 0.2
        self._p_beta = 0.02

        self._last_has_spot: Optional[bool] = None
        self._run_len_s = 0.0
        self._mean_true_s: Optional[float] = None
        self._mean_false_s: Optional[float] = None
        self._run_alpha = 0.15

        self._tdt_len = 0
        self._tdt_sum = 0.0
        self._tdt_mode = 0  # 0 unknown, 1 numeric sum, 2 tuple (start,end), 3 dict duration

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _lazy_init(self):
        if self._inited:
            return
        self._inited = True
        try:
            gap = float(self.env.gap_seconds)
        except Exception:
            gap = 60.0
        self._gap = gap
        # weak priors: expect some alternation but low availability
        self._mean_true_s = 10.0 * gap
        self._mean_false_s = 20.0 * gap

    def _update_availability_stats(self, has_spot: bool):
        gap = self._gap
        self._p = (1.0 - self._p_beta) * self._p + self._p_beta * (1.0 if has_spot else 0.0)

        if self._last_has_spot is None:
            self._last_has_spot = has_spot
            self._run_len_s = gap
            return

        if has_spot == self._last_has_spot:
            self._run_len_s += gap
            return

        # state transition: close previous run and update mean
        if self._last_has_spot:
            prev = self._mean_true_s if self._mean_true_s is not None else self._run_len_s
            self._mean_true_s = (1.0 - self._run_alpha) * prev + self._run_alpha * self._run_len_s
        else:
            prev = self._mean_false_s if self._mean_false_s is not None else self._run_len_s
            self._mean_false_s = (1.0 - self._run_alpha) * prev + self._run_alpha * self._run_len_s

        self._last_has_spot = has_spot
        self._run_len_s = gap

    def _get_work_done(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            self._tdt_len = 0
            self._tdt_sum = 0.0
            self._tdt_mode = 0
            return 0.0

        try:
            n = len(tdt)
        except Exception:
            # unknown structure
            self._tdt_len = 0
            self._tdt_sum = 0.0
            self._tdt_mode = 0
            return 0.0

        if n < self._tdt_len:
            self._tdt_len = 0
            self._tdt_sum = 0.0
            self._tdt_mode = 0

        if self._tdt_mode == 0 and n > 0:
            x = tdt[0]
            if isinstance(x, (int, float)):
                self._tdt_mode = 1
            elif isinstance(x, (tuple, list)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                self._tdt_mode = 2
            elif isinstance(x, dict):
                self._tdt_mode = 3
            else:
                self._tdt_mode = 0

        if self._tdt_mode == 1:
            # numeric durations
            for i in range(self._tdt_len, n):
                v = tdt[i]
                if isinstance(v, (int, float)):
                    self._tdt_sum += float(v)
                else:
                    # fallback recompute
                    self._tdt_sum = 0.0
                    for vv in tdt:
                        if isinstance(vv, (int, float)):
                            self._tdt_sum += float(vv)
                    break
        elif self._tdt_mode == 2:
            # (start,end) segments
            for i in range(self._tdt_len, n):
                seg = tdt[i]
                try:
                    self._tdt_sum += float(seg[1]) - float(seg[0])
                except Exception:
                    # fallback recompute
                    self._tdt_sum = 0.0
                    for s in tdt:
                        try:
                            self._tdt_sum += float(s[1]) - float(s[0])
                        except Exception:
                            pass
                    break
        elif self._tdt_mode == 3:
            # dict entries with duration-like fields
            for i in range(self._tdt_len, n):
                d = tdt[i]
                if not isinstance(d, dict):
                    continue
                if "duration" in d and isinstance(d["duration"], (int, float)):
                    self._tdt_sum += float(d["duration"])
                elif "work" in d and isinstance(d["work"], (int, float)):
                    self._tdt_sum += float(d["work"])
                elif "end" in d and "start" in d and isinstance(d["end"], (int, float)) and isinstance(d["start"], (int, float)):
                    self._tdt_sum += float(d["end"]) - float(d["start"])
        else:
            # unknown: try to sum numeric values
            total = 0.0
            for vv in tdt:
                if isinstance(vv, (int, float)):
                    total += float(vv)
            self._tdt_sum = total

        self._tdt_len = n
        return float(self._tdt_sum)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_availability_stats(has_spot)

        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = 0.0
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0
        try:
            H = float(self.restart_overhead)
        except Exception:
            H = 0.0

        done = self._get_work_done()
        remaining = task_duration - done
        if remaining <= 0.0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        slack = time_left - remaining

        gap = self._gap
        end_buffer = max(2.0 * gap, 2.0 * H)

        # Hard commit to on-demand if we cannot afford further uncertainty.
        if slack <= end_buffer or time_left <= remaining + end_buffer:
            self._committed_od = True

        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Conservative near the end even if not committed.
        if slack < (3.0 * H + gap):
            if has_spot:
                return ClusterType.ON_DEMAND
            return ClusterType.ON_DEMAND

        if has_spot:
            # If currently on-demand, only switch back if spot runs are likely long enough.
            if last_cluster_type == ClusterType.ON_DEMAND:
                mean_true = self._mean_true_s if self._mean_true_s is not None else 10.0 * gap
                min_run = max(6.0 * H, 10.0 * gap, 15.0 * 60.0)
                if self._p < 0.15 or mean_true < min_run:
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot: decide between waiting (NONE) and on-demand.
        # Use required compute rate to avoid overusing slack.
        need_rate = remaining / max(time_left, 1e-9)
        if need_rate > 0.97:
            return ClusterType.ON_DEMAND

        mean_false = self._mean_false_s if self._mean_false_s is not None else (gap / max(self._p, 0.05))
        pause_buffer = max(2.0 * gap, 2.0 * H)

        # If we can likely wait out an outage without consuming too much slack, wait.
        if self._p > 0.05 and slack >= (mean_false + pause_buffer):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

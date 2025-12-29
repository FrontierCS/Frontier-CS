import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args

        self._last_elapsed: Optional[float] = None

        self._prev_spot_obs: Optional[bool] = None
        self._c00 = 20.0
        self._c01 = 1.0
        self._c10 = 1.0
        self._c11 = 4.0

        self._no_spot_streak = 0
        self._spot_streak = 0

        self._committed_on_demand = False
        self._od_hold_until = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    @staticmethod
    def _is_number(x: Any) -> bool:
        return isinstance(x, (int, float)) and not isinstance(x, bool)

    def _work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if self._is_number(td):
            return float(td)
        if isinstance(td, dict):
            if "duration" in td and self._is_number(td["duration"]):
                return float(td["duration"])
            if "done" in td and self._is_number(td["done"]):
                return float(td["done"])
            if "start" in td and "end" in td and self._is_number(td["start"]) and self._is_number(td["end"]):
                return max(0.0, float(td["end"]) - float(td["start"]))
            return 0.0

        if not isinstance(td, (list, tuple)):
            return 0.0

        vals = []
        seg_total = 0.0
        has_segments = False

        for e in td:
            if e is None:
                continue
            if self._is_number(e):
                vals.append(float(e))
                continue
            if isinstance(e, dict):
                if "duration" in e and self._is_number(e["duration"]):
                    seg_total += float(e["duration"])
                    has_segments = True
                    continue
                if "start" in e and "end" in e and self._is_number(e["start"]) and self._is_number(e["end"]):
                    seg_total += max(0.0, float(e["end"]) - float(e["start"]))
                    has_segments = True
                    continue
                continue
            if isinstance(e, (list, tuple)) and len(e) >= 2 and self._is_number(e[0]) and self._is_number(e[1]):
                a = float(e[0])
                b = float(e[1])
                seg_total += max(0.0, b - a)
                has_segments = True
                continue

        if has_segments:
            return max(0.0, seg_total)

        if not vals:
            return 0.0

        # Heuristic: if list looks cumulative (nondecreasing and last reasonable), use last.
        nondecreasing = all(vals[i] <= vals[i + 1] + 1e-9 for i in range(len(vals) - 1))
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        elapsed = float(getattr(getattr(self, "env", None), "elapsed_seconds", 0.0) or 0.0)

        if nondecreasing:
            last = vals[-1]
            if 0.0 <= last <= max(task_duration * 1.05, elapsed * 1.05, last + 1.0):
                # If sum is wildly larger than task_duration, it's likely cumulative samples.
                if sum(vals) > max(task_duration * 1.2, 1.0) and last <= task_duration * 1.2:
                    return max(0.0, last)

        return max(0.0, sum(vals))

    def _reset_episode_state(self):
        self._prev_spot_obs = None
        self._c00 = 20.0
        self._c01 = 1.0
        self._c10 = 1.0
        self._c11 = 4.0
        self._no_spot_streak = 0
        self._spot_streak = 0
        self._committed_on_demand = False
        self._od_hold_until = 0.0

    def _update_spot_markov(self, has_spot: bool):
        if self._prev_spot_obs is not None:
            prev = 1 if self._prev_spot_obs else 0
            curr = 1 if has_spot else 0
            if prev == 0 and curr == 0:
                self._c00 += 1.0
            elif prev == 0 and curr == 1:
                self._c01 += 1.0
            elif prev == 1 and curr == 0:
                self._c10 += 1.0
            else:
                self._c11 += 1.0
        self._prev_spot_obs = has_spot

        if has_spot:
            self._spot_streak += 1
            self._no_spot_streak = 0
        else:
            self._no_spot_streak += 1
            self._spot_streak = 0

    def _estimate_transition_probs(self):
        p01 = self._c01 / max(self._c00 + self._c01, 1e-9)  # P(0->1)
        p10 = self._c10 / max(self._c10 + self._c11, 1e-9)  # P(1->0)
        p01 = min(max(p01, 1e-6), 1.0 - 1e-6)
        p10 = min(max(p10, 1e-6), 1.0 - 1e-6)
        return p01, p10

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 60.0) or 60.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        r = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if self._last_elapsed is None or elapsed < self._last_elapsed - 1e-9:
            self._reset_episode_state()
        self._last_elapsed = elapsed

        self._update_spot_markov(has_spot)

        done = self._work_done_seconds()
        remaining_work = max(0.0, task_duration - done)
        time_left = max(0.0, deadline - elapsed)
        if remaining_work <= 1e-6:
            return ClusterType.NONE
        if time_left <= 1e-6:
            return ClusterType.NONE

        slack = time_left - remaining_work

        p01, p10 = self._estimate_transition_probs()
        expected_wait = gap / max(p01, 1e-6)
        expected_uptime = gap / max(p10, 1e-6)

        # Cap for sanity
        expected_wait = min(expected_wait, time_left)
        expected_uptime = min(expected_uptime, time_left)

        # Estimate expected overhead burden if we keep participating in spot cycling.
        p_avail = p01 / (p01 + p10)
        interrupt_rate_per_sec = (p10 * p_avail) / max(gap, 1e-6)
        expected_interruptions = interrupt_rate_per_sec * time_left
        expected_overhead_time = expected_interruptions * r

        # Hard feasibility guard: if we don't basically run continuously, we risk missing deadline.
        hard_guard = (time_left <= remaining_work + r + gap) or (slack <= r + gap)

        if hard_guard:
            self._committed_on_demand = True

        # If expected overhead alone can eat most slack, stop chasing spot.
        if not self._committed_on_demand:
            if slack <= 0.0:
                self._committed_on_demand = True
            else:
                if expected_overhead_time >= max(0.9 * slack, 2.0 * r):
                    self._committed_on_demand = True

        if self._committed_on_demand:
            if last_cluster_type != ClusterType.ON_DEMAND:
                self._od_hold_until = max(self._od_hold_until, elapsed + max(6.0 * gap, 2.0 * r, 1800.0))
            return ClusterType.ON_DEMAND

        # Hysteresis / amortization controls.
        switch_to_spot_min_uptime = max(2.0 * r, 8.0 * gap, 1800.0)  # ~30min minimum
        wait_instead_of_od_max_wait = max(2.0 * r, 6.0 * gap)        # if outage expected shorter than this, waiting can be better
        slack_needed_to_wait = expected_wait + max(3.0 * r, 2.0 * gap)

        # If slack is very comfortable, we can be more willing to wait rather than flip to OD.
        generous_slack = slack >= max(2.0 * 3600.0, 10.0 * r)

        # Respect OD hold time to avoid flapping.
        if last_cluster_type == ClusterType.ON_DEMAND and elapsed < self._od_hold_until:
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.ON_DEMAND:
            if has_spot and slack >= max(3.0 * r, 1800.0) and expected_uptime >= switch_to_spot_min_uptime:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        if last_cluster_type == ClusterType.SPOT:
            if has_spot:
                # If slack is getting tight, avoid taking more spot risk.
                if slack <= max(4.0 * r, 3600.0) and expected_overhead_time >= 0.5 * slack:
                    self._committed_on_demand = True
                    self._od_hold_until = max(self._od_hold_until, elapsed + max(6.0 * gap, 2.0 * r, 1800.0))
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            # Spot unavailable: either wait (NONE) if outage likely short and slack allows,
            # or go OD and hold to amortize restart.
            if generous_slack and expected_wait <= wait_instead_of_od_max_wait and slack >= slack_needed_to_wait:
                return ClusterType.NONE

            self._od_hold_until = max(self._od_hold_until, elapsed + max(6.0 * gap, 2.0 * r, 1800.0))
            return ClusterType.ON_DEMAND

        # last_cluster_type == NONE (or other unexpected)
        if has_spot:
            return ClusterType.SPOT

        if generous_slack and expected_wait <= wait_instead_of_od_max_wait and slack >= slack_needed_to_wait:
            return ClusterType.NONE

        self._od_hold_until = max(self._od_hold_until, elapsed + max(6.0 * gap, 2.0 * r, 1800.0))
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
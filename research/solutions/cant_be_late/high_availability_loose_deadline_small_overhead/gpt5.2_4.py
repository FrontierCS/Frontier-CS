import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass

        self._committed_to_od = False
        self._total_steps = 0
        self._spot_steps = 0
        self._unavail_streak_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_work_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if not td:
            return 0.0

        try:
            first = td[0]
        except Exception:
            return 0.0

        if isinstance(first, (int, float)):
            vals = []
            for x in td:
                if isinstance(x, (int, float)) and math.isfinite(float(x)):
                    vals.append(float(x))
            if not vals:
                return 0.0
            monotonic = True
            for i in range(1, len(vals)):
                if vals[i] < vals[i - 1]:
                    monotonic = False
                    break
            if monotonic:
                return max(0.0, vals[-1])
            s = 0.0
            for v in vals:
                if v > 0:
                    s += v
            return max(0.0, s)

        if isinstance(first, (tuple, list)):
            total = 0.0
            for seg in td:
                if not isinstance(seg, (tuple, list)) or len(seg) < 2:
                    continue
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    d = float(b) - float(a)
                    if d > 0 and math.isfinite(d):
                        total += d
            return max(0.0, total)

        if isinstance(first, dict):
            total = 0.0
            for seg in td:
                if not isinstance(seg, dict):
                    continue
                if "duration" in seg and isinstance(seg["duration"], (int, float)):
                    d = float(seg["duration"])
                    if d > 0 and math.isfinite(d):
                        total += d
                    continue
                if "start" in seg and "end" in seg and isinstance(seg["start"], (int, float)) and isinstance(seg["end"], (int, float)):
                    d = float(seg["end"]) - float(seg["start"])
                    if d > 0 and math.isfinite(d):
                        total += d
            return max(0.0, total)

        return 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        if env is None:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)

        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        self._total_steps += 1
        if has_spot:
            self._spot_steps += 1
            self._unavail_streak_seconds = 0.0
        else:
            self._unavail_streak_seconds += max(0.0, gap)

        done = self._compute_work_done_seconds()
        remaining_work = max(0.0, task_duration - done)
        remaining_time = max(0.0, deadline - elapsed)

        if remaining_work <= 1e-9:
            return ClusterType.NONE

        # Posterior mean for spot availability with Beta(1,1) prior
        p_est = (self._spot_steps + 1.0) / (self._total_steps + 2.0)
        p_est = min(0.99, max(0.01, p_est))

        # If we switch to OD now, account for a restart overhead on the switch (conservative)
        need_od = remaining_work
        if last_cluster_type != ClusterType.ON_DEMAND:
            need_od += restart_overhead

        base_commit_buffer = 2.0 * 3600.0
        extra_commit_buffer = (1.0 - p_est) * 4.0 * 3600.0
        commit_buffer = base_commit_buffer + extra_commit_buffer

        # Hard feasibility check
        if remaining_time <= need_od + max(gap, 1.0):
            self._committed_to_od = True

        # Risk-based commitment when slack is getting small
        if not self._committed_to_od and remaining_time <= need_od + commit_buffer:
            self._committed_to_od = True

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Not committed: prefer SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # No spot: if already on OD, keep OD until spot returns (avoid churn)
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work

        # Wait a bit for spot to come back if we have ample slack and spot has been fairly available
        per_outage_wait_max = min(1800.0, max(300.0, 0.05 * max(0.0, slack)))
        can_wait = (
            p_est >= 0.60
            and slack > (commit_buffer + per_outage_wait_max + restart_overhead)
            and self._unavail_streak_seconds < per_outage_wait_max
        )

        if can_wait:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
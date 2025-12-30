from typing import Any, Optional, Iterable
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


def _sum_done_seconds(task_done_time: Any) -> float:
    if task_done_time is None:
        return 0.0
    # Common cases:
    # - float/int total seconds
    # - list of floats (durations)
    # - list of (start, end) pairs
    total = 0.0
    try:
        if isinstance(task_done_time, (int, float)):
            return float(task_done_time)
        if isinstance(task_done_time, dict):
            # If dict has 'total' or similar
            for k in ('total', 'sum', 'seconds', 'time'):
                if k in task_done_time and isinstance(task_done_time[k], (int, float)):
                    return float(task_done_time[k])
        if isinstance(task_done_time, Iterable):
            for seg in task_done_time:
                if isinstance(seg, (int, float)):
                    total += float(seg)
                elif isinstance(seg, (list, tuple)):
                    if len(seg) == 2 and all(isinstance(x, (int, float)) for x in seg):
                        s, e = seg
                        total += max(0.0, float(e) - float(s))
                    else:
                        for x in seg:
                            if isinstance(x, (int, float)):
                                total += float(x)
        return float(total)
    except Exception:
        return 0.0


class Solution(Strategy):
    NAME = "cant_be_late_jit_od_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self.od_committed: bool = False

        # Optional tuning knobs (seconds). Keep minimal to avoid early OD.
        self.safety_margin_seconds: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _must_commit_to_od(self, now: float, remain: float) -> bool:
        # If we're already on OD, we are committed.
        if self.od_committed:
            return True

        # Conservative: assume one restart overhead when starting OD.
        overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Latest time to start OD so that we still finish by deadline:
        # now_start + overhead + remain <= deadline
        # now_start <= deadline - (overhead + remain)
        latest_start = float(getattr(self, "deadline", 0.0)) - (remain + overhead + self.safety_margin_seconds)

        # If current time >= latest start time, we must commit to OD.
        return now >= latest_start

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If we've already started OD previously, keep using OD to avoid extra overhead/risk.
        if last_cluster_type == ClusterType.ON_DEMAND:
            self.od_committed = True

        # Compute remaining work
        total_duration: float = float(getattr(self, "task_duration", 0.0) or 0.0)
        done_seconds: float = _sum_done_seconds(getattr(self, "task_done_time", None))
        remain: float = max(0.0, total_duration - done_seconds)

        if remain <= 0.0:
            # Finished: do nothing to avoid extra cost
            return ClusterType.NONE

        now: float = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)

        # Commit to OD if necessary to guarantee deadline.
        if self._must_commit_to_od(now, remain):
            self.od_committed = True

        if self.od_committed:
            return ClusterType.ON_DEMAND

        # Not committed to OD yet:
        # Prefer SPOT when available; otherwise wait (NONE) until we must commit to OD.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
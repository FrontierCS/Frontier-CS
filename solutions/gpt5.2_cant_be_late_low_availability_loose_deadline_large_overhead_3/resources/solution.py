import math
from typing import Any, Optional

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "slack_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except Exception:
            try:
                super().__init__()
            except Exception:
                pass
        self._committed_to_od = False
        self._args = args

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_done_seconds(self) -> float:
        td = getattr(self, "task_duration", None)
        if td is None:
            td = float("inf")

        # Prefer any explicit progress fields if present (not guaranteed by API, but safe to check).
        for name in (
            "task_done_seconds",
            "task_progress_seconds",
            "work_done_seconds",
            "done_seconds",
            "progress_seconds",
        ):
            v = getattr(self.env, name, None)
            if isinstance(v, (int, float)) and math.isfinite(v):
                return float(max(0.0, min(float(v), float(td))))

        tdt = getattr(self, "task_done_time", None)
        if not tdt:
            return 0.0

        # If it's already a scalar by chance.
        if isinstance(tdt, (int, float)):
            v = float(tdt)
            if math.isfinite(v):
                return float(max(0.0, min(v, float(td))))
            return 0.0

        if not isinstance(tdt, (list, tuple)):
            return 0.0

        # Try interpret as list of segments or durations.
        done = 0.0
        nums = []
        monotonic_nondec = True
        prev = None

        for seg in tdt:
            if isinstance(seg, (int, float)) and math.isfinite(float(seg)):
                x = float(seg)
                nums.append(x)
                if prev is not None and x < prev - 1e-9:
                    monotonic_nondec = False
                prev = x
                continue

            if isinstance(seg, (list, tuple)) and len(seg) >= 2:
                a, b = seg[0], seg[1]
                if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    a = float(a)
                    b = float(b)
                    if math.isfinite(a) and math.isfinite(b):
                        if b > a:
                            done += (b - a)
                        continue

            # Try object with start/end attributes
            a = getattr(seg, "start", None)
            b = getattr(seg, "end", None)
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                a = float(a)
                b = float(b)
                if math.isfinite(a) and math.isfinite(b) and b > a:
                    done += (b - a)
                    continue

            # Unrecognized element: ignore for safety.
            continue

        if nums:
            s = float(sum(nums))
            last = float(nums[-1])
            # Heuristic: if it looks like cumulative progress checkpoints, use last.
            if monotonic_nondec and last >= 0.0 and s > float(td) * 1.05 and last <= float(td) + 1e-6:
                done += last
            else:
                done += s

        if not math.isfinite(done):
            done = 0.0
        if td != float("inf"):
            done = min(done, float(td))
        return max(0.0, done)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, stay there to minimize restart risk.
        done = self._compute_done_seconds()
        task_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining = max(0.0, task_duration - done)

        if remaining <= 0.0:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_left = max(0.0, deadline - elapsed)

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Estimated extra overhead if we decide to start/transition to on-demand now.
        switching_to_od_overhead = 0.0
        if last_cluster_type != ClusterType.ON_DEMAND:
            switching_to_od_overhead = restart

        slack = time_left - remaining
        effective_slack_if_od_now = slack - switching_to_od_overhead

        # Hard feasibility trigger: if we wait any longer, discrete stepping / restart overhead may make us miss.
        hard_margin = max(restart, 2.0 * gap, 600.0)  # at least 10 minutes
        if time_left <= remaining + switching_to_od_overhead + hard_margin:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Risk buffers (in seconds).
        commit_slack = max(3.0 * restart, 2.0 * gap, 1800.0)  # at least 30 minutes
        wait_slack = commit_slack + max(restart, 2.0 * gap, 1800.0)  # hysteresis

        # If we're getting close (in slack sense), commit to OD even if spot is currently available.
        if effective_slack_if_od_now <= commit_slack:
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # No spot: wait for spot while we still have enough slack; otherwise start OD.
        if effective_slack_if_od_now > wait_slack:
            return ClusterType.NONE

        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

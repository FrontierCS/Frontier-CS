from typing import Any, Iterable
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "hedged_deadline_spot_v1"

    def __init__(self, args: Any = None):
        super().__init__(args)
        self.force_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _total_done_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0

        # If already a numeric value
        if isinstance(td, (int, float)):
            return max(float(td), 0.0)

        total = 0.0

        def is_number(x: Any) -> bool:
            return isinstance(x, (int, float))

        try:
            iterable: Iterable = td  # type: ignore
        except TypeError:
            try:
                return max(float(td), 0.0)
            except Exception:
                return 0.0

        for seg in iterable:
            try:
                if is_number(seg):
                    total += float(seg)
                else:
                    # Try segment like (start, end)
                    try:
                        length = len(seg)  # type: ignore[arg-type]
                    except Exception:
                        continue
                    if length >= 2:
                        try:
                            start = float(seg[0])
                            end = float(seg[1])
                            total += max(end - start, 0.0)
                        except Exception:
                            continue
                    elif length == 1:
                        try:
                            total += float(seg[0])
                        except Exception:
                            continue
            except Exception:
                continue

        return max(total, 0.0)

    def _compute_state(self):
        done = self._total_done_seconds()
        try:
            task_duration = float(self.task_duration)
        except Exception:
            task_duration = 0.0
        remaining = max(task_duration - done, 0.0)

        try:
            elapsed = float(self.env.elapsed_seconds)
        except Exception:
            elapsed = 0.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = elapsed

        time_left = max(deadline - elapsed, 0.0)
        slack = time_left - remaining
        return remaining, time_left, slack

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        remaining, time_left, slack = self._compute_state()

        # If task finished or no time left, do nothing.
        if remaining <= 0.0 or time_left <= 0.0:
            self.force_od = False
            return ClusterType.NONE

        # Once we decide to commit to on-demand, never go back to spot.
        if self.force_od:
            return ClusterType.ON_DEMAND

        # Time step and restart overhead for safety margin.
        try:
            dt = float(getattr(self.env, "gap_seconds", 0.0))
        except Exception:
            dt = 0.0
        try:
            overhead = float(getattr(self, "restart_overhead", 0.0))
        except Exception:
            overhead = 0.0

        # Commit margin: enough to cover one step of no progress plus one restart overhead.
        commit_slack = max(dt + overhead, 2.0 * dt)

        # If slack is tight, immediately switch to and stick with on-demand.
        if slack <= commit_slack:
            self.force_od = True
            return ClusterType.ON_DEMAND

        # Pre-commit regime: prioritize spot when available; otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

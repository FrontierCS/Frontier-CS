import math
from typing import Any, List

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v2"

    def __init__(self, args=None):
        try:
            super().__init__(args)
        except Exception:
            pass
        self.args = args
        self._committed_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _sum_task_done(self) -> float:
        # Attempt to robustly compute total work done from task_done_time
        total = 0.0
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            return 0.0
        try:
            return float(sum(tdt))
        except Exception:
            pass
        # Try parsing various possible structures
        for item in tdt:
            try:
                total += float(item)
                continue
            except Exception:
                pass
            try:
                # If tuple/list [start, end]
                if isinstance(item, (list, tuple)) and len(item) == 2:
                    a, b = item
                    total += max(0.0, float(b) - float(a))
                    continue
            except Exception:
                pass
            try:
                # Dict with 'dur' or 'duration'
                if isinstance(item, dict):
                    if "dur" in item:
                        total += float(item["dur"])
                        continue
                    if "duration" in item:
                        total += float(item["duration"])
                        continue
            except Exception:
                pass
            try:
                # Object with attribute dur/duration
                d = getattr(item, "dur", None)
                if d is None:
                    d = getattr(item, "duration", 0.0)
                total += float(d or 0.0)
            except Exception:
                pass
        return total

    def _remaining_work(self) -> float:
        try:
            done = self._sum_task_done()
            remaining = max(0.0, float(self.task_duration) - float(done))
            return remaining
        except Exception:
            # Conservative fallback: assume no progress tracked
            try:
                return float(self.task_duration)
            except Exception:
                return 0.0

    def _safe_margin_seconds(self) -> float:
        # Safety margin beyond restart_overhead to account for step discretization.
        try:
            g = float(self.env.gap_seconds)
        except Exception:
            g = 60.0
        return 2.0 * g

    def _should_commit_to_on_demand(self, remaining_work: float, time_left: float) -> bool:
        # Commit if time left <= remaining work + restart_overhead + small safety margin
        try:
            oh = float(self.restart_overhead)
        except Exception:
            oh = 0.0
        margin = self._safe_margin_seconds()
        threshold = remaining_work + oh + margin
        return time_left <= threshold

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Access environment safely
        try:
            now = float(self.env.elapsed_seconds)
            g = float(self.env.gap_seconds)
        except Exception:
            now, g = 0.0, 60.0
        try:
            deadline = float(self.deadline)
        except Exception:
            deadline = now + 3600.0
        try:
            oh = float(self.restart_overhead)
        except Exception:
            oh = 0.0

        time_left = max(0.0, deadline - now)
        remaining_work = self._remaining_work()

        # If done, stop
        if remaining_work <= 0.0:
            self._committed_to_od = False
            return ClusterType.NONE

        # If we're already committed to OD, keep using it
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Determine drop-dead threshold
        safe_extra = self._safe_margin_seconds()
        need_time_if_switch_now = remaining_work + oh + safe_extra

        # If we are close to deadline, commit to OD
        if self._should_commit_to_on_demand(remaining_work, time_left):
            self._committed_to_od = True
            return ClusterType.ON_DEMAND

        # Not yet drop-dead: prefer spot if available
        if has_spot:
            # If currently on-demand, only switch back to spot if we have enough slack to
            # cover two overheads (switch to SPOT now and possibly back to OD later).
            if last_cluster_type == ClusterType.ON_DEMAND:
                slack = time_left - remaining_work
                # Need room for two overheads plus safety to avoid thrash
                required_slack = (2.0 * oh) + (2.0 * safe_extra)
                if slack >= required_slack:
                    return ClusterType.SPOT
                # Otherwise, stay on OD to avoid paying overhead twice near the end
                return ClusterType.ON_DEMAND
            # If not on-demand, take spot
            return ClusterType.SPOT

        # Spot not available:
        # If we're on on-demand already, continue OD
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # Decide to wait for spot or switch to on-demand
        # We can afford to wait one more step if after waiting one step,
        # we still have enough time to finish remaining work plus one overhead and safety.
        can_wait_one_step = (time_left - g) >= (remaining_work + oh + safe_extra)

        if can_wait_one_step:
            # Wait for spot to reappear
            return ClusterType.NONE

        # Not safe to wait: switch to on-demand
        self._committed_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

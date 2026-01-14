import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy."""

    NAME = "cant_be_late_safe_spot"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Normalize core parameters to scalar seconds.
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(td[0])
        elif td is None:
            self._task_duration = float(config["duration"]) * 3600.0
        else:
            self._task_duration = float(td)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        elif ro is None:
            self._restart_overhead = float(config["overhead"]) * 3600.0
        else:
            self._restart_overhead = float(ro)

        dl = getattr(self, "deadline", None)
        if dl is None:
            self._deadline = float(config["deadline"]) * 3600.0
        else:
            self._deadline = float(dl)

        # Internal bookkeeping for efficient progress tracking.
        self._done_sum = 0.0
        self._prev_done_len = 0
        self._gap_seconds = None
        self._committed_to_on_demand = False

        return self

    def _update_done_sum(self) -> None:
        """Incrementally track total completed work to avoid O(n) sums each step."""
        tdt = self.task_done_time
        prev_len = self._prev_done_len
        cur_len = len(tdt)
        if cur_len > prev_len:
            total = 0.0
            for i in range(prev_len, cur_len):
                total += tdt[i]
            self._done_sum += total
            self._prev_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached totals.
        self._update_done_sum()

        # Initialize gap size once.
        if self._gap_seconds is None:
            self._gap_seconds = float(self.env.gap_seconds)

        # Remaining work.
        remaining_work = self._task_duration - self._done_sum
        if remaining_work <= 0.0:
            # Task already effectively done; no need to run more.
            return ClusterType.NONE

        # If we've already decided to use On-Demand to guarantee completion, keep using it.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        current_time = self.env.elapsed_seconds
        R = self._restart_overhead

        # Conservative margin: one full step of lost work + one restart overhead.
        margin = self._gap_seconds + R

        # S = current time + remaining work + one possible future restart overhead.
        safety_measure = current_time + remaining_work + R
        threshold = self._deadline - margin

        # If we're too close to the deadline to risk Spot/idle (even with one more restart),
        # commit to On-Demand and never go back.
        if safety_measure > threshold:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Safe zone: prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # No Spot available and still in safe zone: wait (NONE) to avoid expensive On-Demand.
        return ClusterType.NONE
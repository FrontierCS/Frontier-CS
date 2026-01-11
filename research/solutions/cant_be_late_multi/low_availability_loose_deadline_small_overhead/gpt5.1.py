import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Safe, cost-aware multi-region scheduling strategy."""

    NAME = "safe_slack_spot_strategy_v1"

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

        # Internal trackers for efficient progress accounting
        self._work_done = 0.0
        self._last_task_done_index = 0
        self._eps = 1e-6
        return self

    def _update_work_done(self) -> None:
        """Incrementally track total work done to avoid O(n) sum each step."""
        tdt = self.task_done_time
        idx = self._last_task_done_index
        n = len(tdt)
        if idx < n:
            # Sum only newly added segments
            total_new = 0.0
            for i in range(idx, n):
                total_new += tdt[i]
            self._work_done += total_new
            self._last_task_done_index = n

    def _get_task_duration(self) -> float:
        td = self.task_duration
        if isinstance(td, (list, tuple)):
            return float(td[0])
        return float(td)

    def _get_restart_overhead(self) -> float:
        ro = self.restart_overhead
        if isinstance(ro, (list, tuple)):
            return float(ro[0])
        return float(ro)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update cached progress
        self._update_work_done()

        task_duration = self._get_task_duration()
        restart_overhead = self._get_restart_overhead()

        # Remaining computational work (seconds)
        remaining_work = task_duration - self._work_done
        if remaining_work <= self._eps:
            # Task finished; avoid extra cost.
            return ClusterType.NONE

        # Time remaining until deadline (seconds)
        time_remaining = self.deadline - self.env.elapsed_seconds
        if time_remaining <= 0:
            # Deadline already reached or exceeded; nothing can fix this,
            # but run ON_DEMAND to minimize further delay.
            return ClusterType.ON_DEMAND

        gap = self.env.gap_seconds

        # Determine if it's safe to spend the next step without guaranteed
        # progress (i.e., risk using Spot or idling). We use a conservative
        # worst-case: next step yields zero work, and we still may need a
        # single restart_overhead before an all-OnDemand catch-up.
        #
        # Condition for safety after one risky step:
        #   (time_remaining - gap) >= remaining_work + restart_overhead
        #
        # If this holds, we can afford one more step of risk. Otherwise,
        # we must run On-Demand now.
        can_risk_next_step = (time_remaining - gap) >= (remaining_work + restart_overhead - self._eps)

        if can_risk_next_step:
            # Risk-tolerant region: prefer cheap Spot; if unavailable, wait.
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            # Safety-critical region: commit to On-Demand to guarantee completion.
            return ClusterType.ON_DEMAND
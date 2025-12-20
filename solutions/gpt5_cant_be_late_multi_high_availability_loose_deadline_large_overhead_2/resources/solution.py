import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_late_multi"

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

        # Strategy state
        self._commit_on_demand = False
        self._no_spot_streak = 0
        return self

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time)
        remaining = max(0.0, self.task_duration - done)
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already finished, no need to run
        remaining_work = self._remaining_work()
        if remaining_work <= 0.0:
            self._commit_on_demand = False
            return ClusterType.NONE

        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        gap = float(self.env.gap_seconds)
        # Conservative safety margin: allow for one lost step and an extra overhead
        safety_margin = gap + self.restart_overhead

        # Track streak of no-spot in current region
        if has_spot:
            self._no_spot_streak = 0
        else:
            self._no_spot_streak = min(self._no_spot_streak + 1, 10**9)

        # If we are already on ON_DEMAND and have pending overhead, keep ON_DEMAND to avoid resetting overhead.
        if last_cluster_type == ClusterType.ON_DEMAND and getattr(self, "remaining_restart_overhead", 0.0) > 0.0:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # Time required to finish if we commit to ON_DEMAND now.
        # If already on ON_DEMAND, no new overhead; otherwise, we will incur a restart overhead.
        commit_overhead = self.restart_overhead if last_cluster_type != ClusterType.ON_DEMAND else getattr(self, "remaining_restart_overhead", 0.0)
        commit_required = remaining_work + commit_overhead

        # Enter commit mode if we're close to deadline with limited slack
        if time_left <= commit_required + safety_margin:
            self._commit_on_demand = True

        # If we have committed to ON_DEMAND, stick to it to avoid additional overheads.
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # If Spot is available and we are not committed, prefer Spot to minimize cost.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available. Decide to wait (NONE) or switch to ON_DEMAND.
        # Compute safe wait time before we must commit to ON_DEMAND (including margin).
        # If we can afford to wait at least one step, wait; otherwise switch to ON_DEMAND.
        safe_wait_time = time_left - (remaining_work + self.restart_overhead + safety_margin)

        if safe_wait_time >= gap:
            return ClusterType.NONE

        # Otherwise, use ON_DEMAND to ensure we do not miss the deadline.
        self._commit_on_demand = True
        return ClusterType.ON_DEMAND

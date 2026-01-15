import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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

        # Internal state for handling multiple traces/runs.
        self._committed_to_on_demand = False
        self._last_elapsed = -1.0
        return self

    def _maybe_reset_internal_state(self):
        # Detect new run by elapsed time reset.
        if self._last_elapsed < 0.0 or self.env.elapsed_seconds < self._last_elapsed:
            self._committed_to_on_demand = False
        self._last_elapsed = self.env.elapsed_seconds

    def _remaining_work(self) -> float:
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        rem = self.task_duration - done
        return rem if rem > 0.0 else 0.0

    def _should_commit_on_demand(self, last_cluster_type: ClusterType) -> bool:
        slack = self.deadline - self.env.elapsed_seconds
        remaining_work = self._remaining_work()

        # Overhead needed if we choose (or continue) On-Demand now.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_needed = self.remaining_restart_overhead
        else:
            overhead_needed = self.restart_overhead

        # Commit if we no longer have buffer to tolerate a switch later.
        # This ensures finishing before deadline if we stay on On-Demand.
        return slack <= (remaining_work + overhead_needed + 1e-9)

    def _rotate_region(self):
        n = self.env.get_num_regions()
        if n <= 1:
            return
        cur = self.env.get_current_region()
        nxt = (cur + 1) % n
        self.env.switch_region(nxt)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_reset_internal_state()

        # If finished (or effectively finished), do nothing.
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # Once committed, stay on On-Demand to guarantee finish.
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        # Decide whether to commit to On-Demand now.
        if self._should_commit_on_demand(last_cluster_type):
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we have slack: wait (NONE) and try another region next step.
        self._rotate_region()
        return ClusterType.NONE
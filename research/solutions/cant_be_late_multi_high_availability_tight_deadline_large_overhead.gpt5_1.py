import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_heuristic_v1"

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
        # Internal state
        self._committed_on_demand = False
        self._initialized = False
        return self

    def _init_once(self):
        if self._initialized:
            return
        # Lazy init with environment info
        self._initialized = True
        self._region_count = max(1, int(self.env.get_num_regions()))
        self._safety_margin = float(self.env.gap_seconds)  # commit earlier by one gap
        self._last_region = self.env.get_current_region() if hasattr(self.env, "get_current_region") else 0

    def _remaining_work_seconds(self) -> float:
        done = sum(self.task_done_time) if hasattr(self, "task_done_time") and self.task_done_time else 0.0
        rem = max(self.task_duration - done, 0.0)
        return rem

    def _should_commit_on_demand(self, now: float, rem: float) -> bool:
        # Latest time to commit to OD to be safe: deadline - rem - restart_overhead - safety_margin
        commit_by = self.deadline - rem - self.restart_overhead - self._safety_margin
        return now >= commit_by

    def _rotate_region_on_spot_miss(self):
        if self._region_count <= 1:
            return
        cur = self.env.get_current_region()
        if cur is None:
            cur = self._last_region if hasattr(self, "_last_region") else 0
        nxt = (int(cur) + 1) % self._region_count
        self.env.switch_region(nxt)
        self._last_region = nxt

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_once()

        # If already committed to On-Demand, keep using it to avoid extra overheads and guarantee finish.
        if self._committed_on_demand:
            return ClusterType.ON_DEMAND

        now = float(self.env.elapsed_seconds)
        rem = self._remaining_work_seconds()

        # If no work left, do nothing
        if rem <= 0.0:
            return ClusterType.NONE

        # Decide if we must commit to On-Demand to guarantee finishing before deadline.
        if self._should_commit_on_demand(now, rem):
            self._committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Prefer Spot when available.
        if has_spot:
            # Stay in current region if spot available; switching could incur restart overheads.
            return ClusterType.SPOT

        # Spot not available now, wait (NONE) and try another region next step to find spot.
        self._rotate_region_on_spot_miss()
        return ClusterType.NONE
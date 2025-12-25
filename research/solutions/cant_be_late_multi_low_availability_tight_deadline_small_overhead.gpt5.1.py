import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType

# Backward compatibility if enum member is named "None" instead of "NONE".
if not hasattr(ClusterType, "NONE") and hasattr(ClusterType, "None"):
    setattr(ClusterType, "NONE", getattr(ClusterType, "None"))


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on deadline safety and low cost."""

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

        # Internal state initialization flag
        self._internal_inited = False
        return self

    def _initialize_internal(self):
        if getattr(self, "_internal_inited", False):
            return
        self._internal_inited = True

        # Total required work in seconds (single task).
        self.total_work = float(self.task_duration)

        # Track completed work incrementally.
        self.completed_work = 0.0
        self._last_task_done_len = len(getattr(self, "task_done_time", []))

        # Precompute safety margins (in seconds).
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)

        # Minimal slack required if we switch to on-demand only now.
        # We conservatively add one step duration plus one restart overhead.
        self._safe_commit_slack = gap + overhead

        # Worst-case additional slack that might be lost in a single risky step:
        # full step without progress plus another restart overhead.
        self._worst_loss_per_step = gap + 2.0 * overhead

        # Commit threshold: once slack <= this, we must stop taking risk.
        # Ensures after at most one more risky step we still have _safe_commit_slack.
        self._commit_threshold = self._safe_commit_slack + self._worst_loss_per_step

        # Once set, always use ON_DEMAND.
        self._force_on_demand = False

    def _update_completed_work(self):
        """Incrementally update completed work using newly appended segments."""
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_done_len:
            new_work = 0.0
            for v in self.task_done_time[self._last_task_done_len : cur_len]:
                new_work += float(v)
            self.completed_work += new_work
            self._last_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_internal()
        self._update_completed_work()

        # If task already complete, no further compute is needed.
        if self.completed_work >= self.total_work:
            return ClusterType.NONE

        remaining_work = self.total_work - self.completed_work
        time_left = self.deadline - self.env.elapsed_seconds

        # If somehow out of time, aggressively use on-demand.
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Slack if we immediately switch to on-demand-only.
        slack = time_left - remaining_work

        # Decide whether to latch into on-demand phase.
        if not self._force_on_demand:
            if slack <= self._commit_threshold:
                self._force_on_demand = True

        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Risk-taking phase: prefer Spot when available, otherwise wait (NONE).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE

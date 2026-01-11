import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with slack-aware Spot/On-Demand policy."""

    NAME = "cant_be_late_multi_v1"

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
        self._done_sum = 0.0
        self._last_task_done_len = 0
        self._runtime_inited = False

        return self

    # ----- Internal helpers -----

    def _initialize_runtime_params(self) -> None:
        if self._runtime_inited:
            return

        env = self.env

        gap = float(getattr(env, "gap_seconds", 0.0))
        if gap <= 0.0:
            # Fallback to 1s step if gap is missing; keeps logic well-defined.
            gap = 1.0
        self._gap = gap

        self._overhead = float(self.restart_overhead)
        self._total_slack = max(float(self.deadline - self.task_duration), 0.0)

        # Slack needed to safely idle for one full step and still be able to
        # complete later using only on-demand: restart overhead + one gap.
        self._idle_slack_needed = self._overhead + self._gap

        # "Panic" slack threshold below which we always use on-demand to avoid
        # additional preemption/overhead risk.
        safe_commit_slack = 3.0 * self._overhead + 2.0 * self._gap
        if self._total_slack > 0.0:
            panic = min(safe_commit_slack, self._total_slack)
        else:
            panic = 0.0
        # Ensure at least one overhead's worth of slack when we commit.
        self._panic_slack = max(self._overhead, panic)

        self._runtime_inited = True

    def _update_done_sum(self) -> None:
        """Incrementally maintain the sum of task_done_time in O(1) per step."""
        td = self.task_done_time
        n = len(td)
        last_n = self._last_task_done_len
        if n > last_n:
            total_new = 0.0
            for i in range(last_n, n):
                total_new += td[i]
            self._done_sum += total_new
            self._last_task_done_len = n

    # ----- Core decision logic -----

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization that depends on env.
        self._initialize_runtime_params()
        self._update_done_sum()

        env = self.env

        remaining_work = self.task_duration - self._done_sum
        if remaining_work <= 0.0:
            # Task already finished.
            return ClusterType.NONE

        elapsed = float(env.elapsed_seconds)
        time_left = self.deadline - elapsed

        if time_left <= 0.0:
            # At or past deadline with remaining work; best effort with On-Demand.
            return ClusterType.ON_DEMAND

        # Slack is the wall-clock time we can afford to waste from now on.
        slack = time_left - remaining_work

        # Danger zone: very little slack remaining. Always use On-Demand.
        if slack <= self._panic_slack:
            return ClusterType.ON_DEMAND

        # Comfortable slack: prefer cheaper Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide between idling (NONE) and On-Demand.
        if slack >= self._idle_slack_needed:
            # Enough slack to idle for one more step and still complete later on OD.
            return ClusterType.NONE

        # Not enough slack to keep idling; switch to On-Demand.
        return ClusterType.ON_DEMAND
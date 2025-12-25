import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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

        # Cache important parameters in seconds for robustness.
        self._deadline_seconds = float(config["deadline"]) * 3600.0
        self._task_duration_seconds = float(config["duration"]) * 3600.0
        self._restart_overhead_seconds = float(config["overhead"]) * 3600.0

        # Internal state
        self._policy_initialized = False
        self.committed_to_on_demand = False

        return self

    def _initialize_policy(self):
        # Initialize per-run policy constants lazily, once env is available.
        gap = getattr(self.env, "gap_seconds", None)
        if gap is None:
            gap = 3600.0
        self._gap_seconds = gap

        # Use cached restart overhead if available, otherwise fall back.
        self._restart_overhead = getattr(
            self, "_restart_overhead_seconds", getattr(self, "restart_overhead", 0.0)
        )

        self._policy_initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not getattr(self, "_policy_initialized", False):
            self._initialize_policy()

        # Retrieve environment and task state.
        elapsed = getattr(self.env, "elapsed_seconds", 0.0)
        gap = getattr(self.env, "gap_seconds", self._gap_seconds)

        deadline = getattr(self, "_deadline_seconds", getattr(self, "deadline", 0.0))
        total_duration = getattr(
            self, "_task_duration_seconds", getattr(self, "task_duration", 0.0)
        )
        restart_overhead = getattr(
            self, "_restart_overhead_seconds", getattr(self, "restart_overhead", 0.0)
        )

        task_segments = getattr(self, "task_done_time", None)
        if task_segments:
            progress = 0.0
            for x in task_segments:
                progress += x
        else:
            progress = 0.0

        remaining_work = total_duration - progress
        if remaining_work <= 0.0:
            # Task completed (or very close); avoid extra cost.
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            # Deadline has passed; nothing useful to do.
            return ClusterType.NONE

        # Once we commit to ON_DEMAND, we keep using it to avoid extra overhead
        # and ensure deterministic completion.
        if getattr(self, "committed_to_on_demand", False):
            return ClusterType.ON_DEMAND

        # Conservative safety margin:
        # B = gap + restart_overhead, so that max time drop per step (gap + overhead)
        # cannot push us past the minimal required time after the next decision.
        safety_margin = gap + restart_overhead

        # If we are close enough to the deadline that relying on Spot is unsafe,
        # switch to ON_DEMAND and stay there until completion.
        if remaining_time <= remaining_work + restart_overhead + safety_margin:
            self.committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Before commitment, use Spot whenever available (cheapest option).
        if has_spot:
            return ClusterType.SPOT

        # Spot is unavailable and we still have ample slack: wait to save cost.
        return ClusterType.NONE

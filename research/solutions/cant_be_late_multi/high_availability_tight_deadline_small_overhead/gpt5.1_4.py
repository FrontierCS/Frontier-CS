import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Cant-Be-Late multi-region scheduling strategy."""

    NAME = "cant_be_late_safe_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        # Basic required arguments for MultiRegionStrategy.
        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )

        # Pass through any additional fields if present (e.g., trace_files),
        # so MultiRegionStrategy can use them if it expects them.
        for key in ("trace_files", "trace_dir"):
            if key in config:
                setattr(args, key, config[key])

        super().__init__(args)

        # Internal bookkeeping (lazy-initialized in _step once env is ready).
        self._initialized_internal = False
        self._done_cache_len = 0
        self._done_cache_sum = 0.0
        self._safety_slack = None
        self.force_on_demand = False

        return self

    def _lazy_init_internal(self):
        """Initialize internal state on first _step call."""
        if self._initialized_internal:
            return
        self._initialized_internal = True

        # Initialize cached progress.
        self._done_cache_len = len(self.task_done_time)
        self._done_cache_sum = float(sum(self.task_done_time)) if self.task_done_time else 0.0

        # Safety slack: ensure enough extra time to pay for a final restart
        # overhead plus a couple of time steps of discretization.
        gap = float(getattr(self.env, "gap_seconds", 0.0))
        self._safety_slack = float(self.restart_overhead) + 2.0 * gap

        self.force_on_demand = False

    def _update_done_cache(self):
        """Efficiently maintain total work done using incremental sum."""
        current_len = len(self.task_done_time)
        if current_len > self._done_cache_len:
            # Sum only new segments since last call.
            new_segments = self.task_done_time[self._done_cache_len : current_len]
            if new_segments:
                self._done_cache_sum += float(sum(new_segments))
            self._done_cache_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Ensure internal fields are ready (env is guaranteed to exist here).
        self._lazy_init_internal()

        # Update cached work-done total.
        self._update_done_cache()
        work_done = self._done_cache_sum
        work_remaining = max(self.task_duration - work_done, 0.0)

        # If task already finished, avoid running anything further.
        if work_remaining <= 0.0:
            return ClusterType.NONE

        # Time left until deadline.
        time_left = self.deadline - self.env.elapsed_seconds

        # If somehow past deadline already, stop running to avoid extra cost.
        if time_left <= 0.0:
            return ClusterType.NONE

        # Slack: extra time beyond what is strictly needed to finish remaining
        # work assuming ideal uninterrupted run at full speed (1 sec work/sec).
        slack = time_left - work_remaining

        # Once we decide to go on-demand to guarantee completion, we never
        # revert to spot to avoid further restart overheads or risk.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # If slack is too small to safely pay for at least one full restart
        # overhead (plus discretization margin), immediately commit to
        # on-demand and stay there for the remainder of the job.
        if slack <= self._safety_slack:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # We are comfortably ahead of schedule: prefer Spot when available.
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we still have ample slack: pause to save cost.
        # This is safe because we only switch to on-demand once slack shrinks
        # near the safety margin.
        return ClusterType.NONE
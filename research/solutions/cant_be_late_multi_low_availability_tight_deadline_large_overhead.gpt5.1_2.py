import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def __init__(self):
        # Defer base-class initialization to solve(), where we have the spec.
        pass

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )

        # Initialize base strategy/environment.
        super().__init__(args)

        # Initialize internal state.
        self._init_internal_state()
        return self

    def _init_internal_state(self) -> None:
        # Commitment flag: once we switch to guaranteed on-demand, we never go back.
        self.committed_on_demand = False

        # Track total work done without O(N) summation every step.
        self._total_work_done = 0.0
        self._last_task_done_index = 0

        # Region statistics (not heavily used but kept for potential extensions).
        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = 1
        self.num_regions = num_regions
        self.region_spot_success = [0] * num_regions
        self.region_total_observations = [0] * num_regions

        # Determine the enum member for "no cluster" robustly.
        if hasattr(ClusterType, "NONE"):
            self._none_cluster_type = ClusterType.NONE
        elif hasattr(ClusterType, "None"):
            # In case the enum uses "None" instead of "NONE".
            self._none_cluster_type = getattr(ClusterType, "None")
        else:
            # Fallback: this should not happen given the problem spec.
            # Use ON_DEMAND as a safe default if NONE is unavailable (very unlikely).
            self._none_cluster_type = ClusterType.ON_DEMAND

    def _update_region_stats(self, has_spot: bool) -> None:
        # Update simple statistics for the current region's spot availability.
        try:
            r = self.env.get_current_region()
        except Exception:
            return
        if 0 <= r < self.num_regions:
            self.region_total_observations[r] += 1
            if has_spot:
                self.region_spot_success[r] += 1

    def _update_work_done(self) -> None:
        # Incrementally track total work done from task_done_time list.
        td = self.task_done_time
        idx = self._last_task_done_index
        if td is None:
            return
        n = len(td)
        if idx < n:
            # Add only new segments since last call.
            self._total_work_done += sum(td[idx:n])
            self._last_task_done_index = n

    def _get_remaining_work(self) -> float:
        self._update_work_done()
        remaining = self.task_duration - self._total_work_done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Update region stats with current observation.
        self._update_region_stats(has_spot)

        # Compute remaining work.
        remaining_work = self._get_remaining_work()

        # If task already finished, no need to run more.
        if remaining_work <= 0.0:
            return self._none_cluster_type

        # Time bookkeeping.
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if time_left <= 0.0:
            # Past deadline (should not normally happen); nothing useful to do.
            return self._none_cluster_type

        gap = getattr(self.env, "gap_seconds", 60.0)

        # Safety margin to account for discretization/overhead modeling uncertainties.
        # We commit to on-demand early enough to comfortably meet the deadline.
        margin = max(3.0 * gap, 2.0 * self.restart_overhead)

        # Conservative estimate of time needed if we commit to ON_DEMAND from now on.
        # We assume at most one restart overhead after commitment.
        needed_time_commit = self.restart_overhead + remaining_work

        # If we've already committed to ON_DEMAND, stay on it until completion.
        if self.committed_on_demand:
            return ClusterType.ON_DEMAND

        # Decide whether it's time to commit to ON_DEMAND to guarantee meeting deadline.
        if time_left <= needed_time_commit + margin:
            self.committed_on_demand = True
            return ClusterType.ON_DEMAND

        # Not yet committed: use cheap SPOT whenever available, otherwise idle to save cost.
        if has_spot:
            return ClusterType.SPOT

        # SPOT unavailable and we still have plenty of slack: pause.
        return self._none_cluster_type

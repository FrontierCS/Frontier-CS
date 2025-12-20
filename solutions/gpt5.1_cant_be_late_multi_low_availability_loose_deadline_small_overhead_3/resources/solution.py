import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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
        super().__init__(args)

        # Policy state
        self._policy_initialized = False
        self._cached_done = 0.0
        self._last_task_segments = 0
        self._commit_on_demand = False

        # Cache scalar versions of key parameters if available
        # Fallback to attributes provided by base class
        try:
            self._task_duration = float(self.task_duration)
        except Exception:
            # In case task_duration is a list/tuple
            self._task_duration = float(self.task_duration[0])

        try:
            self._restart_overhead = float(self.restart_overhead)
        except Exception:
            self._restart_overhead = float(self.restart_overhead[0])

        try:
            self._deadline = float(self.deadline)
        except Exception:
            # If deadline is stored differently, fall back directly
            self._deadline = float(getattr(self, "deadline", 0.0))

        # Will be set on first _step call when env is ready
        self._gap = None

        return self

    def _initialize_policy_state_if_needed(self):
        if self._policy_initialized:
            return
        # env should be initialized by now
        self._gap = float(getattr(self.env, "gap_seconds", 1.0))
        # Start with whatever work may already be recorded
        td = getattr(self, "task_done_time", [])
        if td:
            # One-time sum; afterwards we incrementally maintain this
            self._cached_done = float(sum(td))
            self._last_task_segments = len(td)
        else:
            self._cached_done = 0.0
            self._last_task_segments = 0
        self._commit_on_demand = False
        self._policy_initialized = True

    def _update_completed_work(self):
        """Incrementally update cached completed work based on task_done_time list."""
        td = self.task_done_time
        n = len(td)
        if n > self._last_task_segments:
            inc = 0.0
            for i in range(self._last_task_segments, n):
                inc += td[i]
            self._cached_done += inc
            self._last_task_segments = n

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
        # Lazy initialization when env is ready
        self._initialize_policy_state_if_needed()

        # Update cached completed work
        self._update_completed_work()

        # Compute remaining work
        remaining_work = self._task_duration - self._cached_done
        if remaining_work <= 0.0:
            # Task is effectively done; no need to run further
            return ClusterType.NONE

        # Time left until deadline
        time_left = self._deadline - float(self.env.elapsed_seconds)

        # If somehow past deadline and still not done, just run (penalty unavoidable)
        if time_left <= 0.0:
            # Prefer cheaper SPOT if available, otherwise ON_DEMAND
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # Decide if we must commit to ON_DEMAND to safely finish by deadline.
        # Required worst-case time from now if we start ON_DEMAND and never stop:
        #   restart_overhead + remaining_work
        # Add one gap for discretization safety.
        required_time = remaining_work + self._restart_overhead + self._gap

        if (not self._commit_on_demand) and (required_time >= time_left):
            self._commit_on_demand = True

        # Once committed, always run ON_DEMAND until finish
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        # Opportunistic phase: use SPOT when available, otherwise idle to save cost
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

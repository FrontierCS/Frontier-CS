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

        # Internal state for the strategy
        self._internal_initialized = False
        self._done_work = 0.0
        self._last_task_done_len = 0
        self._committed_to_od = False
        self._max_spot_seconds = 0.0
        self._safety_margin = 0.0
        self._task_duration_scalar = None
        self._deadline_scalar = None
        self._restart_overhead_scalar = None
        self._gap_seconds = None

        return self

    def _initialize_internal(self) -> None:
        """Lazy initialization of derived parameters."""
        # Task duration (seconds)
        task_dur = getattr(self, "task_duration", 0.0)
        if isinstance(task_dur, (list, tuple)):
            task_dur = task_dur[0]
        self._task_duration_scalar = float(task_dur)

        # Deadline (seconds)
        deadline = getattr(self, "deadline", 0.0)
        if isinstance(deadline, (list, tuple)):
            deadline = deadline[0]
        self._deadline_scalar = float(deadline)

        # Restart overhead (seconds)
        overhead = getattr(self, "restart_overhead", 0.0)
        if isinstance(overhead, (list, tuple)):
            overhead = overhead[0]
        self._restart_overhead_scalar = float(overhead)

        # Gap seconds per step
        self._gap_seconds = float(getattr(self.env, "gap_seconds", 1.0))

        # Total slack if we used on-demand only from time 0 (worst-case 0 spot progress)
        # Approx minimal OD time ~= task_duration + restart_overhead (+ small discretization).
        slack_total = max(
            0.0,
            self._deadline_scalar - (self._task_duration_scalar + self._restart_overhead_scalar),
        )

        g = self._gap_seconds
        h = self._restart_overhead_scalar

        # If slack is extremely tight, do not risk spot at all.
        if slack_total <= g:
            self._max_spot_seconds = 0.0
            self._safety_margin = slack_total
        else:
            # Safety margin for modeling errors & discretization.
            # At most 50% of slack, capped at 5*(h + g), and at least one gap.
            margin = min(slack_total * 0.5, 5.0 * (h + g))
            if margin < g:
                margin = g
            # Ensure margin leaves some room for spot play; if not, disable spot.
            if margin > slack_total - g:
                margin = max(g, slack_total - g)
            if margin < 0.0:
                margin = 0.0
            self._safety_margin = margin
            # Max time we can afford to "waste" on spot (assuming zero useful progress)
            # while still being able to finish with OD only.
            self._max_spot_seconds = max(0.0, slack_total - margin - g)

        self._internal_initialized = True

    def _update_done_work(self) -> None:
        """Incrementally track total work done to avoid O(n) summation each step."""
        segments = self.task_done_time
        length = len(segments)
        if length > self._last_task_done_len:
            new_segments = segments[self._last_task_done_len:length]
            # Sum only new segments; each segment is processed once overall.
            self._done_work += float(sum(new_segments))
            self._last_task_done_len = length

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        # Lazy initialization of derived parameters
        if not self._internal_initialized:
            self._initialize_internal()

        # Update total work done so far
        self._update_done_work()

        # If task completed, stop running any cluster
        if self._done_work >= self._task_duration_scalar - 1e-6:
            return ClusterType.NONE

        now = float(self.env.elapsed_seconds)

        # Hard safety: if current time beyond deadline, just use ON_DEMAND
        # (penalty is already incurred if we truly missed, but OD is still best effort).
        if now >= self._deadline_scalar:
            return ClusterType.ON_DEMAND

        # Commit to on-demand if we've exhausted our "spot budget" in time.
        if (not self._committed_to_od) and now >= self._max_spot_seconds:
            self._committed_to_od = True

        # Additional dynamic safety: if remaining time is barely enough to finish
        # the *remaining* work with on-demand (plus overhead and margin), commit now.
        if not self._committed_to_od:
            remaining_time = self._deadline_scalar - now
            work_remaining = max(0.0, self._task_duration_scalar - self._done_work)
            # Conservative estimate of time needed if we switch to OD now.
            required_od_time = work_remaining + self._restart_overhead_scalar + self._gap_seconds
            if remaining_time <= required_od_time + self._safety_margin:
                self._committed_to_od = True

        # Once committed, always use on-demand until finished.
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Spot phase: use spot when available, otherwise pause (no-cost NONE).
        if has_spot:
            return ClusterType.SPOT
        return ClusterType.NONE
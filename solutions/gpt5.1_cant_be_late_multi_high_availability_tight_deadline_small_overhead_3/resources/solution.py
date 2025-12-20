import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Deadline-safe, cost-aware multi-region scheduling strategy."""

    NAME = "deadline_safe_spot_first"

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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Strategy:
        - Always guarantee finishing before the deadline under worst-case Spot behavior.
        - Use Spot when available and when it's safe to "risk" one more timestep with
          potentially no progress.
        - When Spot is unavailable but it is still safe to wait, idle (NONE) to avoid
          expensive On-Demand.
        - Once it's no longer safe to risk delay, switch to On-Demand and never go
          back to Spot.
        """
        env = self.env

        # Basic state
        t = env.elapsed_seconds
        gap = env.gap_seconds

        # Total work done so far
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        total_work = self.task_duration
        remaining_work = max(total_work - done, 0.0)

        # Time left until the hard deadline
        time_left = self.deadline - t

        # If task is finished or we are past the deadline, stop spending money.
        if remaining_work <= 0 or time_left <= 0:
            return ClusterType.NONE

        overhead = self.restart_overhead

        # If even switching to On-Demand immediately would barely be enough (or not enough),
        # choose On-Demand to maximize chance of meeting the deadline.
        # This also handles any numerical / modeling edge cases safely.
        if time_left <= overhead + remaining_work:
            return ClusterType.ON_DEMAND

        # Check if it's safe (under worst-case) to "risk" one more timestep where we
        # might make no progress (e.g., Spot preempted or we idle).
        #
        # Worst-case plan for one more risky step:
        #   - We lose 'gap' seconds with zero progress.
        #   - After that, we may need to pay one restart_overhead and finish all remaining work.
        #
        # So we require:
        #   time_left >= gap + overhead + remaining_work
        safe_to_risk_one_step = time_left >= (gap + overhead + remaining_work)

        if safe_to_risk_one_step:
            # We have enough slack to afford one more "risky" timestep.
            if has_spot:
                # Use cheap Spot; any progress we get is a bonus.
                return ClusterType.SPOT
            else:
                # No Spot right now, and it's safe to wait hoping Spot appears later.
                return ClusterType.NONE

        # Not safe to risk further delay: lock in On-Demand until finish.
        return ClusterType.ON_DEMAND

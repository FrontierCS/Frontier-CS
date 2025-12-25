import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with slack-aware Spot/On-Demand selection."""

    NAME = "my_strategy"

    def solve(self, spec_path: str) -> "Solution":
        """Initialize the solution from spec_path config."""
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Policy parameters (all in seconds).
        # We work with slack B = time_left - (remaining_work + remaining_restart_overhead).
        # B_LOW  : when slack falls below this, permanently switch to On-Demand only.
        # B_HIGH : when slack below this, avoid idling when Spot is unavailable (use OD),
        #          but still use Spot when available.
        # Must ensure B_LOW >= restart_overhead for deadline safety.
        self.buffer_low = 2.0 * self.restart_overhead
        self.buffer_high = 4.0 * self.restart_overhead
        if self.buffer_high < self.buffer_low:
            self.buffer_high = self.buffer_low

        # Once we lock into On-Demand, we never go back to Spot.
        self._lock_on_demand = False

        return self

    def _compute_slack(self) -> float:
        """Compute current slack B (seconds)."""
        elapsed = self.env.elapsed_seconds
        time_left = self.deadline - elapsed
        if time_left < 0.0:
            time_left = 0.0

        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = self.task_duration - done
        if remaining_work < 0.0:
            remaining_work = 0.0

        overhead_remaining = getattr(self, "remaining_restart_overhead", 0.0)
        remaining_total = remaining_work + overhead_remaining
        return time_left - remaining_total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """

        # If task already done (shouldn't usually be called), do nothing.
        done = sum(self.task_done_time) if self.task_done_time else 0.0
        if done >= self.task_duration:
            return ClusterType.NONE

        # Compute current slack.
        slack = self._compute_slack()

        # If we've already committed to On-Demand, keep using it.
        if self._lock_on_demand:
            return ClusterType.ON_DEMAND

        # If slack is very small or negative, immediately lock to On-Demand.
        if slack <= 0.0 or slack <= self.buffer_low:
            self._lock_on_demand = True
            return ClusterType.ON_DEMAND

        # Moderate slack zone: avoid idling, but still favor Spot when available.
        if slack <= self.buffer_high:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

        # Comfortable slack zone: aggressively use Spot; idle when Spot unavailable.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

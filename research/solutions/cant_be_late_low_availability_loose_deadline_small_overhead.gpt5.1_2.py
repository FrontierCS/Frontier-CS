from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        # Initialize per-run state if needed
        self.use_on_demand_only = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env

        # Detect new episode or uninitialized state
        if not hasattr(self, "use_on_demand_only") or env.elapsed_seconds == 0:
            self.use_on_demand_only = False

        # If we've already committed to on-demand, stay there
        if self.use_on_demand_only:
            return ClusterType.ON_DEMAND

        elapsed = env.elapsed_seconds
        deadline = self.deadline
        task_duration = self.task_duration
        restart_overhead = self.restart_overhead
        gap = env.gap_seconds if env.gap_seconds is not None else 0.0

        remaining_wall = deadline - elapsed

        # If we're at or past the deadline, must use on-demand
        if remaining_wall <= 0:
            self.use_on_demand_only = True
            return ClusterType.ON_DEMAND

        # Conservative assumption: no progress has been made yet.
        # Thus remaining compute time upper bound is full task_duration.
        remaining_compute_upper = task_duration

        # Time needed to safely finish if we switch to pure on-demand now:
        # remaining_compute_upper + one restart_overhead + one gap for discretization.
        time_needed_upper = remaining_compute_upper + restart_overhead + max(gap, 0.0)

        # If remaining wall-clock time is at most what we need, commit to on-demand.
        if remaining_wall <= time_needed_upper:
            self.use_on_demand_only = True
            return ClusterType.ON_DEMAND

        # We still have ample slack: use spot when available, otherwise pause.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
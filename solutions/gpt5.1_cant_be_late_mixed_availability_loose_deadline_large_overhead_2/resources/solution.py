from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_dynamic_v1"

    def __init__(self, args=None):
        super().__init__(args)
        self.args = args
        self.force_on_demand = False

    def solve(self, spec_path: str) -> "Solution":
        # No special initialization needed; return self as required.
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Compute completed work so far.
        done_segments = getattr(self, "task_done_time", None)
        if done_segments is None:
            completed = 0.0
        else:
            completed = float(sum(done_segments))

        total_duration = float(getattr(self, "task_duration", 0.0) or 0.0)
        remaining_work = max(total_duration - completed, 0.0)

        # If task already done, stop using any instances.
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Time until deadline.
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        time_to_deadline = deadline - elapsed

        # If somehow past deadline, just use on-demand (can't fix lateness, but obey API).
        if time_to_deadline <= 0.0:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # If we've already entered the guaranteed-completion phase, stay on on-demand.
        if self.force_on_demand:
            return ClusterType.ON_DEMAND

        # Compute safety margin for when to switch permanently to on-demand.
        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        # Extra safety to account for discretization and any uncertainty.
        # Ensure safety_extra > gap so we switch before it's too late even with step granularity.
        safety_extra = max(restart_overhead, 2.0 * gap)

        # Minimum remaining time needed from *now* to safely finish if we switch to on-demand:
        #   restart_overhead (once) + remaining_work + safety_extra
        critical_time_needed = remaining_work + restart_overhead + safety_extra

        # If remaining time is at or below this, we must switch to on-demand permanently.
        if time_to_deadline <= critical_time_needed:
            self.force_on_demand = True
            return ClusterType.ON_DEMAND

        # Risk-accepting phase: prefer spot when available, otherwise idle (NONE).
        if has_spot:
            return ClusterType.SPOT

        # No spot available and not yet in the must-finish phase: wait to save cost.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

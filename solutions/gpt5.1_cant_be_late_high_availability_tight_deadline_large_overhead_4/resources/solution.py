from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _compute_work_done(self) -> float:
        segments = getattr(self, "task_done_time", None)
        if not segments:
            return 0.0
        total = 0.0
        try:
            iterator = iter(segments)
        except TypeError:
            try:
                return float(segments)
            except Exception:
                return 0.0
        for seg in segments:
            try:
                if isinstance(seg, (list, tuple)):
                    if len(seg) >= 2:
                        start = float(seg[0])
                        end = float(seg[1])
                        total += max(0.0, end - start)
                else:
                    total += float(seg)
            except Exception:
                continue
        task_duration = getattr(self, "task_duration", None)
        if task_duration is not None:
            return min(total, float(task_duration))
        return total

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not hasattr(self, "use_on_demand_only"):
            self.use_on_demand_only = False

        # Basic environment data
        elapsed = float(self.env.elapsed_seconds)
        gap = float(self.env.gap_seconds)
        task_duration = float(self.task_duration)
        deadline = float(self.deadline)
        restart_ovhd = float(getattr(self, "restart_overhead", 0.0))

        work_done = self._compute_work_done()
        remaining_work = max(0.0, task_duration - work_done)

        # If task is finished, stop using resources.
        if remaining_work <= 0.0:
            self.use_on_demand_only = False
            return ClusterType.NONE

        time_left = deadline - elapsed

        # If already past deadline, just use on-demand to minimize further delay.
        if time_left <= 0.0:
            self.use_on_demand_only = True
            return ClusterType.ON_DEMAND

        slack = time_left - remaining_work  # allowable non-progress time remaining

        # Safety margins
        safety_gap = 2.0 * gap  # discretization buffer
        commit_threshold = restart_ovhd + safety_gap  # minimal slack to safely commit to OD
        extra_idle_slack = max(3.0 * restart_ovhd, 3600.0)  # allow idling when slack is large
        idle_threshold = commit_threshold + extra_idle_slack

        # If slack already negative, it's impossible to fully recover; use OD anyway.
        if slack <= 0.0:
            self.use_on_demand_only = True
            return ClusterType.ON_DEMAND

        # If we've already committed to on-demand, stick with it.
        if getattr(self, "use_on_demand_only", False):
            return ClusterType.ON_DEMAND

        # If slack is too small to afford more overhead or idle time, commit to OD.
        if slack <= commit_threshold:
            self.use_on_demand_only = True
            return ClusterType.ON_DEMAND

        # Slack is still comfortable.
        if has_spot:
            # Using spot when available preserves slack (progress equals time).
            return ClusterType.SPOT

        # Spot is unavailable.
        # If slack is getting modest, start OD instead of idling.
        if slack <= idle_threshold:
            self.use_on_demand_only = True
            return ClusterType.ON_DEMAND

        # Plenty of slack and no spot: wait for cheaper spot.
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

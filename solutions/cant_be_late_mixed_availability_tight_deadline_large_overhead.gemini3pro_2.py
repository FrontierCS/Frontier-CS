from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "cant_be_late_strategy"

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Calculate current state
        elapsed = self.env.elapsed_seconds
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done
        time_remaining = self.deadline - elapsed
        
        # We calculate a 'projected slack' which represents the safety margin we have
        # assuming we might need to start an instance (incurring overhead).
        # Even if we are currently running, this conservative metric helps decide
        # if we can afford to stop or switch.
        # Slack = Time_Available - (Work_Needed + Restart_Overhead)
        overhead = self.restart_overhead
        slack = time_remaining - (remaining_work + overhead)
        
        # Safety buffer: we want to keep at least 1x overhead duration as a buffer
        # to handle time step granularity and minor uncertainties.
        buffer = overhead

        if has_spot:
            # Spot instances are available.
            if last_cluster_type == ClusterType.ON_DEMAND:
                # We are currently on On-Demand. Switching to Spot saves money but costs time (overhead).
                # We only switch if we have enough slack to pay the switch cost AND maintain our safety buffer.
                # The 'slack' variable already deducts one overhead (for the conservative baseline).
                # Switching consumes an additional overhead (time passes, work doesn't).
                # So we check if: slack > buffer + cost_to_switch
                if slack > buffer + overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND
            else:
                # We are on Spot or None. Prefer Spot.
                # Staying on Spot is always better than switching to OD immediately if Spot is up,
                # because switching to OD incurs immediate overhead, reducing slack.
                return ClusterType.SPOT
        else:
            # Spot instances are unavailable.
            # We must decide whether to wait (NONE) or burn money (ON_DEMAND).
            if slack > buffer:
                # We have enough safety margin to wait for Spot to return.
                return ClusterType.NONE
            else:
                # Margin is tight. We must use On-Demand to guarantee completion.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

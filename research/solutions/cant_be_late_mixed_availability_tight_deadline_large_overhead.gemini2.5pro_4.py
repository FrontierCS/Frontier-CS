import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "slack_heuristic"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes strategy-specific parameters and state.
        """
        # When slack drops below this, use ON_DEMAND if SPOT is unavailable.
        self.SLACK_BUFFER_SECONDS = 1.0 * 3600  # 1 hour

        # Extra slack required to switch from ON_DEMAND back to SPOT for hysteresis.
        self.OD_TO_SPOT_HYSTERESIS_SECONDS = 1.0 * 3600  # 1 hour

        # State variable to lock into ON_DEMAND if deadline is imminent.
        self.on_critical_path = False
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Makes a decision at each timestep based on a slack-based heuristic.
        """
        work_done = sum(end - start for start, end in self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 1e-9:
            return ClusterType.NONE

        elapsed_time = self.env.elapsed_seconds
        time_left_to_deadline = self.deadline - elapsed_time

        # --- Critical Path Safety Net ---
        # Calculate time needed to finish if we use On-Demand from this point.
        time_needed_for_od_finish = work_remaining
        if last_cluster_type != ClusterType.ON_DEMAND:
            time_needed_for_od_finish += self.restart_overhead

        # If time needed is >= time left, we must use On-Demand.
        if time_needed_for_od_finish >= time_left_to_deadline:
            self.on_critical_path = True
        
        # Once on the critical path, stay on On-Demand.
        if self.on_critical_path:
            return ClusterType.ON_DEMAND

        # --- Main Heuristic Logic ---
        current_slack = time_left_to_deadline - work_remaining

        # Case A: We were on ON_DEMAND in the last step.
        if last_cluster_type == ClusterType.ON_DEMAND:
            if not has_spot:
                return ClusterType.ON_DEMAND

            # Spot is available. Check if it's worth switching back from stable OD.
            od_to_spot_slack_threshold = self.SLACK_BUFFER_SECONDS + self.OD_TO_SPOT_HYSTERESIS_SECONDS
            if current_slack > od_to_spot_slack_threshold:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        
        # Case B: We were on SPOT or NONE in the last step.
        else:
            if has_spot:
                return ClusterType.SPOT
            
            # Spot is unavailable. Decide between waiting (NONE) or using ON_DEMAND.
            if current_slack < self.SLACK_BUFFER_SECONDS:
                return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Required factory method for evaluator instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
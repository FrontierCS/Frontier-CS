import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy parameters. These are tuned based on the problem specification.
        """
        # K_PANIC determines the threshold for "panic mode". If the available time slack
        # drops below this many restart_overheads, the strategy will exclusively use
        # ON_DEMAND instances to guarantee progress and avoid deadline failure. A value
        # of 3.0 provides a conservative buffer against a few unexpected preemptions.
        self.K_PANIC = 3.0

        # K_WAIT_FACTOR helps decide whether to wait (NONE) for a SPOT instance when
        # one is not available. The decision is based on a dynamic buffer proportional
        # to the remaining work. This factor is derived from a pessimistic estimate of
        # the effective speed of using SPOT instances, accounting for both availability
        # and preemption risk.
        # Calculation: K_WAIT_FACTOR = 1 / s_eff_pessimistic - 1
        # s_eff_pessimistic = A_pessimistic * (1 - preemption_loss_rate)
        # Using pessimistic availability (A=0.43) and an estimated preemption loss rate.
        self.K_WAIT_FACTOR = 1.42
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        This method implements a three-tiered heuristic strategy based on the
        concept of "on-demand slack" (od_slack). `od_slack` is the time buffer
        we have if we were to complete the rest of the job using only on-demand
        instances.

        The strategy operates in three modes:
        1. Panic Mode: If `od_slack` is critically low, use ON_DEMAND exclusively.
        2. Comfortable Mode: If `od_slack` is very high relative to the remaining
           work, use SPOT when available and wait (NONE) otherwise.
        3. Prudent Mode: In between, use SPOT when available and ON_DEMAND otherwise
           to maintain progress without consuming slack.
        """
        
        # Calculate current state variables
        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        # If the task is completed, do nothing to save costs.
        if work_rem <= 0:
            return ClusterType.NONE

        time_now = self.env.elapsed_seconds
        time_rem = self.deadline - time_now

        # If the deadline has passed, a final attempt to make progress is made,
        # though failure is likely.
        if time_rem <= 0:
            return ClusterType.ON_DEMAND
        
        # The core metric for our decision-making.
        od_slack = time_rem - work_rem

        # --- Strategy Logic ---

        # 1. Panic Mode check
        panic_buffer = self.K_PANIC * self.restart_overhead
        if od_slack < panic_buffer:
            return ClusterType.ON_DEMAND

        # If not in panic mode, the primary choice is SPOT if available.
        if has_spot:
            return ClusterType.SPOT
        else:
            # SPOT is unavailable. Decide between waiting (NONE) or buying
            # guaranteed progress (ON_DEMAND).
            # This decision is based on comparing slack to a dynamic wait buffer.
            wait_buffer_dynamic = self.K_WAIT_FACTOR * work_rem
            
            # 2. Comfortable Mode: Slack is large enough to wait.
            if od_slack > wait_buffer_dynamic:
                return ClusterType.NONE
            # 3. Prudent Mode: Slack is not large enough; must use ON_DEMAND.
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        """
        Instantiates the class from parsed arguments.
        This implementation does not require custom arguments.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
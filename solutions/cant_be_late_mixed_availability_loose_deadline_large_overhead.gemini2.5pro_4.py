import argparse

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "AdaptiveThreeState"

    def solve(self, spec_path: str) -> "Solution":
        self.preemption_count = 0
        self.last_work_done = 0.0
        self.is_first_step = True
        
        # Base buffer to handle volatility, in multiples of restart_overhead.
        # A value of 5.0 means we keep a 5 * 12 min = 1-hour buffer initially.
        self.BASE_BUFFER_FACTOR = 5.0
        
        # How much to increase the buffer per preemption, in multiples of restart_overhead.
        # A value of 1.0 means the buffer grows by 12 minutes for each preemption.
        self.PER_PREEMPTION_BUFFER_FACTOR = 1.0
        
        # If slack is this much larger than the safety buffer, we can afford to wait.
        # Set to 4 hours, a significant portion of the total 22-hour slack.
        self.WAIT_SLACK_MARGIN_SECONDS = 4 * 3600
        
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        current_work_done = sum(end - start for start, end in self.task_done_time)

        if not self.is_first_step:
            # A preemption is assumed if we used SPOT but made no progress.
            # This is a robust way to detect preemptions without complex state.
            if last_cluster_type == ClusterType.SPOT and abs(current_work_done - self.last_work_done) < 1e-9:
                self.preemption_count += 1
        
        self.last_work_done = current_work_done
        if self.is_first_step:
            self.is_first_step = False

        work_remaining = self.task_duration - current_work_done
        # If the job is finished, do nothing to avoid further costs.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # The core of the strategy is an adaptive safety buffer.
        # It grows as we experience more preemptions, making the strategy
        # more conservative in environments with unstable spot instances.
        adaptive_factor = self.BASE_BUFFER_FACTOR + (self.preemption_count * self.PER_PREEMPTION_BUFFER_FACTOR)
        safety_buffer = adaptive_factor * self.restart_overhead

        # --- Three-State Decision Logic ---

        # 1. PANIC MODE: Not enough time left to finish on On-Demand + safety buffer.
        # We must use On-Demand to guarantee completion.
        if time_to_deadline <= work_remaining + safety_buffer:
            return ClusterType.ON_DEMAND
        
        # If not in panic mode, we can afford to use Spot if available.
        if has_spot:
            return ClusterType.SPOT
        
        # If Spot is not available, we decide whether to wait or use On-Demand.
        slack = time_to_deadline - work_remaining
        wait_threshold = safety_buffer + self.WAIT_SLACK_MARGIN_SECONDS
        
        # 2. AGGRESSIVE/WAIT MODE: Plenty of slack.
        # If slack is abundant, we can afford to wait for Spot to become available again.
        if slack > wait_threshold:
            return ClusterType.NONE
            
        # 3. CAUTIOUS MODE: Slack is shrinking.
        # If slack is no longer abundant, make guaranteed progress with On-Demand
        # to preserve remaining slack for future Spot preemptions.
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)

import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    """
    This strategy uses a dynamic safety buffer to decide when to switch from
    cost-saving Spot instances to deadline-guaranteeing On-Demand instances.

    The core idea is to calculate a required "safety buffer" of time at each
    step. If the actual time slack (time until deadline minus remaining work)
    falls below this buffer, the strategy enters a "critical" mode and uses
    On-Demand to ensure progress.

    The safety buffer is dynamic:
    - It starts large, equal to the total initial slack, making the strategy
      initially aggressive in using Spot or waiting for it.
    - It shrinks as the job progresses, converging to a minimum buffer calculated
      to withstand a predefined number of preemptions near the end.

    This approach allows the strategy to be opportunistic and cost-effective
    when there is ample time, and increasingly conservative and risk-averse as
    the deadline approaches or as slack is consumed by preemptions.
    """
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize strategy-specific parameters and state. This is called once
        before the simulation begins.
        """
        # --- Tunable Parameters ---
        # Defines the number of preemptions we want our minimum buffer to be
        # able to withstand. Given low availability zones, a value of 3-5
        # provides a reasonable safety margin.
        self.MIN_BUFFER_PREEMPTIONS = 4.0

        # --- Internal State ---
        # Cache for work_done calculation to avoid re-summing the entire list
        # at every step.
        self.last_len_task_done_time = -1
        self.cached_work_done = 0.0

        # --- Pre-calculated Constants from Environment ---
        # Total slack time available at the beginning of the task.
        self.initial_slack = self.deadline - self.task_duration
        
        # The minimum safety buffer we want to maintain at the end of the job.
        self.min_buffer = self.MIN_BUFFER_PREEMPTIONS * self.restart_overhead
        
        # The minimum buffer cannot be larger than the total slack available.
        # This handles edge cases with very tight deadlines.
        self.min_buffer = min(self.min_buffer, self.initial_slack)
            
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decision-making logic called at each time step.
        """
        # 1. Calculate current progress (with caching for efficiency)
        if len(self.task_done_time) != self.last_len_task_done_time:
            self.cached_work_done = sum(end - start for start, end in self.task_done_time)
            self.last_len_task_done_time = len(self.task_done_time)
        
        work_done = self.cached_work_done
        work_remaining = self.task_duration - work_done

        # If job is finished, do nothing to save cost.
        if work_remaining <= 1e-9:
            return ClusterType.NONE

        # 2. Calculate current time state
        time_to_deadline = self.deadline - self.env.elapsed_seconds
        
        # 3. Handle Point of No Return (PNR)
        # If remaining work is more than or equal to time left, we have zero
        # or negative slack. We must use On-Demand as our only hope.
        if work_remaining >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # 4. Calculate the dynamic safety buffer for the current step
        if self.task_duration > 1e-9:
            progress_fraction = max(0.0, min(1.0, work_done / self.task_duration))
        else:
            # Handle case where task_duration is zero; job is done.
            progress_fraction = 1.0

        # The required buffer linearly interpolates from initial_slack down to min_buffer
        # as the job progresses from 0% to 100% complete.
        safety_buffer = self.min_buffer + (1.0 - progress_fraction) * (self.initial_slack - self.min_buffer)
        
        current_slack = time_to_deadline - work_remaining

        # 5. Make decision based on comparing current slack to our required buffers
        
        # CRITICAL ZONE: Is our actual slack less than our required safety buffer?
        if current_slack < safety_buffer:
            # Yes. We are in danger. We must use On-Demand to guarantee progress.
            return ClusterType.ON_DEMAND
        else:
            # SAFE ZONE: We have sufficient slack. We can prioritize cost savings.
            # Always prefer the cheapest option (Spot) if it's available.
            if has_spot:
                return ClusterType.SPOT
            
            # Spot is not available. Decide between expensive progress (On-Demand)
            # or waiting (None). We transition to a "cautious" mode if our
            # slack drops below our desired minimum endgame buffer.
            if current_slack < self.min_buffer:
                # CAUTIOUS sub-zone: Slack is getting low; use On-Demand.
                return ClusterType.ON_DEMAND
            else:
                # COMFORTABLE sub-zone: Plenty of slack; we can afford to wait.
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """REQUIRED: For evaluator instantiation"""
        args, _ = parser.parse_known_args()
        return cls(args)
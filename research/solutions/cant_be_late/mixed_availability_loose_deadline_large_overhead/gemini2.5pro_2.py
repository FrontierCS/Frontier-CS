import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        Read spec_path for configuration if needed.
        Must return self.
        """
        # This factor determines the safety buffer. A larger factor means switching
        # to On-Demand earlier, making the strategy safer but potentially more
        # expensive. The buffer is proportional to the remaining work.
        # Given the high penalty for failure, a conservative value is chosen.
        # Max theoretical factor is (deadline - task_duration) / task_duration
        # For this problem: (70-48)/48 ~= 0.458. We use 0.35.
        self.BUFFER_FACTOR = 0.35

        # State variables to track progress and events across steps
        self.prev_total_work_done = 0.0
        self.was_preempted = False
        self.on_demand_mode = False  # A latch to stay on On-Demand once triggered

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Called at each time step. Return which cluster type to use next.

        The core logic is to maintain a "safety buffer" of time. If the
        projected time to finish on reliable On-Demand instances eats into this
        buffer, we switch to On-Demand permanently. Otherwise, we opportunistically
        use cheap Spot instances or wait if they are unavailable.
        """
        # If we have already latched into On-Demand mode, stay there to guarantee completion.
        if self.on_demand_mode:
            return ClusterType.ON_DEMAND

        # --- State Update ---

        # Calculate work done since the last step to detect preemptions.
        current_work_done = sum(seg.duration for seg in self.task_done_time)
        work_this_step = current_work_done - self.prev_total_work_done

        # A preemption is detected if we used a Spot instance but made no progress.
        # Conversely, if we made progress, any pending restart overhead is cleared.
        if last_cluster_type == ClusterType.SPOT and work_this_step == 0 and self.env.elapsed_seconds > 0:
            self.was_preempted = True
        elif work_this_step > 0:
            self.was_preempted = False
        
        self.prev_total_work_done = current_work_done

        work_remaining = self.task_duration - current_work_done

        # If the task is finished, do nothing to avoid incurring costs.
        if work_remaining <= 0:
            return ClusterType.NONE

        # --- Decision Logic ---

        # Calculate the total time required to finish if we switch to On-Demand now.
        # This must include any pending restart overhead from a previous preemption.
        pending_overhead = self.restart_overhead if self.was_preempted else 0.0
        on_demand_time_needed = work_remaining + pending_overhead

        # The safety buffer is dynamic, shrinking as the task nears completion.
        safety_buffer = work_remaining * self.BUFFER_FACTOR
        
        # The estimated wall-clock time when the task would finish if run on On-Demand from now.
        estimated_on_demand_finish_time = self.env.elapsed_seconds + on_demand_time_needed
        
        # The effective deadline, moved earlier by our safety buffer.
        deadline_with_buffer = self.deadline - safety_buffer

        # The "urgency" condition: if the projected On-Demand finish time crosses our
        # safety-buffered deadline, we must switch to On-Demand.
        is_urgent = estimated_on_demand_finish_time >= deadline_with_buffer

        if is_urgent:
            self.on_demand_mode = True
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack time. Be cost-effective:
            # use Spot if available, otherwise wait (cost-free).
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        """
        Factory method required by the evaluator for instantiation.
        """
        args, _ = parser.parse_known_args()
        return cls(args)
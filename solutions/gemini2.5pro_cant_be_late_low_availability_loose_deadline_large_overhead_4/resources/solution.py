from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "proportional_control_strategy"

    def solve(self, spec_path: str) -> "Solution":
        # Calculate a target finish time to stay on a safe progress trajectory.
        # This approach aims to finish well before the hard deadline to build a
        # buffer against unpredictable spot availability and preemption overheads.
        
        # Total available slack assuming no preemptions and continuous work.
        initial_slack = self.deadline - self.task_duration
        
        # We define a safety buffer, aiming to finish with this much time to spare.
        # Using half of the total slack is a robust choice that doesn't overfit
        # to specific traces. It makes the strategy conservative, which is
        # important given the high penalty for missing the deadline.
        safety_buffer = initial_slack / 2.0
        
        # This is our internal target for when the task should be completed.
        target_completion_duration = self.deadline - safety_buffer
        
        # Safeguard: if the task is too long to meet our target, we must work
        # at the maximum possible rate.
        if self.task_duration >= target_completion_duration:
            self.target_work_rate = 1.0
        else:
            # Calculate the constant rate of progress (work seconds per wall-clock second)
            # needed to meet our target completion time. This rate forms the baseline
            # for our scheduling decisions.
            self.target_work_rate = self.task_duration / target_completion_duration
            
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Step 1: Calculate current progress and remaining work.
        total_work_done = sum(end - start for start, end in self.task_done_time)
        remaining_work = self.task_duration - total_work_done

        # If the task is already finished, idle to prevent further costs.
        if remaining_work <= 0:
            return ClusterType.NONE

        # Step 2: Assess the current state of the system.
        current_time = self.env.elapsed_seconds
        current_overhead = self.env.remaining_overhead_seconds
        
        # This is the total amount of uninterruptible time required to finish
        # from the current state.
        total_time_needed_to_finish = remaining_work + current_overhead
        time_until_deadline = self.deadline - current_time
        
        # Step 3: Implement a hard safety net to guarantee deadline compliance.
        # If the time needed to finish is greater than or equal to the time
        # remaining, we are on the critical path. We must use a guaranteed
        # resource (On-Demand) to avoid failure. This check overrides all else.
        if total_time_needed_to_finish >= time_until_deadline:
            return ClusterType.ON_DEMAND

        # Step 4: Apply the primary scheduling strategy.
        # Always prefer Spot instances when available due to their low cost.
        if has_spot:
            return ClusterType.SPOT
        else:
            # Spot is not available. We must choose between expensive progress (ON_DEMAND)
            # or cost-free waiting (NONE). The decision is based on whether we
            # are ahead of or behind our target schedule.
            
            # Calculate the amount of work that should have been completed by now
            # to stay on our target trajectory.
            target_work_done_by_now = current_time * self.target_work_rate

            if total_work_done >= target_work_done_by_now:
                # We are on or ahead of schedule. We can afford to wait for a
                # spot instance to become available, thereby saving costs.
                return ClusterType.NONE
            else:
                # We have fallen behind our target schedule. We must use On-Demand
                # to catch up. This prevents us from falling so far behind that
                # the critical safety net is triggered, forcing prolonged and
                # expensive On-Demand usage later.
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

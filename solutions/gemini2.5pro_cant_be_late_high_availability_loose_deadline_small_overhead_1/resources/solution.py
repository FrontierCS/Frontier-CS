import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "adaptive_slack_strategy"

    def solve(self, spec_path: str) -> "Solution":
        self.last_task_done_time_len = 0
        self.current_work_done = 0.0
        self.preempted_in_last_spot_run = False
        
        self.total_steps = 0
        self.spot_available_count = 0
        
        self.p_spot_alpha_prior = 3.0
        self.p_spot_beta_prior = 2.0
        
        self.safety_factor = 2.5

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        new_len = len(self.task_done_time)
        progress_made = False
        if new_len > self.last_task_done_time_len:
            new_segments_sum = sum(self.task_done_time[self.last_task_done_time_len:])
            self.current_work_done += new_segments_sum
            progress_made = True
        
        self.last_task_done_time_len = new_len
        
        if last_cluster_type == ClusterType.SPOT and not progress_made and self.total_steps > 0:
            self.preempted_in_last_spot_run = True
        elif last_cluster_type != ClusterType.NONE and progress_made:
            self.preempted_in_last_spot_run = False

        self.total_steps += 1
        if has_spot:
            self.spot_available_count += 1

        work_remaining = self.task_duration - self.current_work_done
        if work_remaining <= 0:
            return ClusterType.NONE

        current_time = self.env.elapsed_seconds
        time_to_deadline = self.deadline - current_time

        time_needed_for_od = work_remaining
        if self.preempted_in_last_spot_run:
            time_needed_for_od += self.restart_overhead
            
        slack = time_to_deadline - time_needed_for_od

        if slack <= 0:
            return ClusterType.ON_DEMAND

        if has_spot:
            if self.preempted_in_last_spot_run:
                preemption_slack_cost = self.env.gap_seconds
            else:
                preemption_slack_cost = self.env.gap_seconds + self.restart_overhead
            
            if slack > preemption_slack_cost:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND
        else:
            p_spot_est = (self.p_spot_alpha_prior + self.spot_available_count) / \
                         (self.p_spot_alpha_prior + self.p_spot_beta_prior + self.total_steps)
            
            if p_spot_est < 1e-6:
                p_spot_est = 1e-6

            avg_wait_steps = 1.0 / p_spot_est
            wait_time_estimate = avg_wait_steps * self.env.gap_seconds
            
            wait_threshold = self.safety_factor * wait_time_estimate + self.restart_overhead
            
            if slack > wait_threshold:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser: argparse.ArgumentParser):
        args, _ = parser.parse_known_args()
        return cls(args)

import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.state = {
            'remaining_work': None,
            'last_total_done': 0.0,
            'last_time': 0.0,
            'restart_active': False,
            'restart_ends_at': 0.0
        }

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = self.env.elapsed_seconds
        step = self.env.gap_seconds

        # Calculate remaining work
        total_done = sum(end - start for start, end in self.task_done_time)
        remaining_work = self.task_duration - total_done

        # Update restart state
        if self.state['restart_active'] and elapsed >= self.state['restart_ends_at']:
            self.state['restart_active'] = False

        # Track if we were actually running last step
        work_done_this_step = total_done - self.state['last_total_done']
        was_running = work_done_this_step > 0 and last_cluster_type != ClusterType.NONE

        # If we're currently in a restart, no work happens
        if self.state['restart_active']:
            was_running = False

        # Calculate urgency
        time_left = self.deadline - elapsed
        urgency = remaining_work / max(time_left, 1e-6)

        # Decision logic
        # 1. If we're on-demand, continue (guaranteed)
        if last_cluster_type == ClusterType.ON_DEMAND and was_running:
            return ClusterType.ON_DEMAND

        # 2. If we're on spot and it's available, continue
        if last_cluster_type == ClusterType.SPOT and was_running and has_spot:
            return ClusterType.SPOT

        # 3. We're either idle, preempted, or starting fresh
        # Conservative threshold: if we're behind schedule, go on-demand
        # Include restart overhead in time estimation
        estimated_time = remaining_work + (self.restart_overhead if not was_running else 0)
        safety_margin = 1.5  # Extra safety factor
        if time_left < estimated_time * safety_margin or urgency > 0.95:
            if has_spot and time_left > estimated_time * 1.2:  # Less urgent, try spot
                self.state['restart_active'] = True
                self.state['restart_ends_at'] = elapsed + self.restart_overhead
                return ClusterType.SPOT
            return ClusterType.ON_DEMAND

        # 4. Not urgent, prefer spot when available
        if has_spot:
            # Only incur restart if we're not already running
            if not was_running:
                self.state['restart_active'] = True
                self.state['restart_ends_at'] = elapsed + self.restart_overhead
            return ClusterType.SPOT

        # 5. No spot, not urgent - wait
        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

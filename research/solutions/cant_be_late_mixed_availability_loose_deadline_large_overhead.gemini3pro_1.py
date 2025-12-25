import argparse
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "LazySlackStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Optional initialization. Called once before evaluation.
        """
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the cluster type for the next time step based on a slack-based deadline policy.
        """
        # 1. Retrieve environment state
        elapsed = self.env.elapsed_seconds
        gap = self.env.gap_seconds
        deadline = self.deadline
        total_needed = self.task_duration
        restart_overhead = self.restart_overhead
        
        # Calculate remaining work based on completed segments
        work_done = sum(self.task_done_time)
        remaining_work = max(0.0, total_needed - work_done)
        
        # If the task is effectively complete, return NONE to stop incurring costs
        # (Though usually the environment terminates the loop automatically)
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        # 2. Calculate Deadline Safety Threshold
        # Calculate the latest possible moment we must switch to On-Demand (OD) to guarantee completion.
        # If we switch to OD, we need:
        #   - 'remaining_work' seconds of actual compute time.
        #   - 'restart_overhead' seconds to spin up/configure the OD instance.
        # We also add a safety buffer:
        #   - We need at least 'gap' seconds because we are making a decision for the *next* interval.
        #   - We add extra padding (2.0 * gap) to robustness against discretization noise and floating point drift.
        
        time_left = deadline - elapsed
        safety_threshold = remaining_work + restart_overhead + (2.0 * gap)
        
        # 3. Decision Logic
        
        # CRITICAL: If we are approaching the point of no return, force On-Demand.
        # This ensures we meet the hard deadline even if Spot is flaky.
        if time_left <= safety_threshold:
            return ClusterType.ON_DEMAND
            
        # OPTIMIZATION: If we have plenty of slack (time_left > safety_threshold), minimize cost.
        if has_spot:
            # Spot is available and cheap -> Use it.
            return ClusterType.SPOT
        else:
            # Spot is unavailable, but we still have slack.
            # Instead of burning money on expensive On-Demand immediately, we pause (NONE).
            # We wait for Spot availability or for the slack to run out (triggering the safety check above).
            return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
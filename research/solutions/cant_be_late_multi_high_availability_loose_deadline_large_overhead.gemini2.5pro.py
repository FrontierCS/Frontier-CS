import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    An adaptive, multi-region scheduling strategy that balances the low cost of
    Spot instances with the reliability of On-Demand instances to meet a deadline.

    The core logic is as follows:
    1.  **Safety First (Panic Mode)**: It continuously calculates the time
        required to finish the job using only On-Demand instances. If the
        time remaining to the deadline gets dangerously close to this
        worst-case completion time, it switches to On-Demand exclusively to
        guarantee finishing on time and avoid a massive penalty.

    2.  **Cost Optimization (Opportunistic Spot)**: When not in danger of
        missing the deadline, the strategy aggressively uses Spot instances
        whenever they are available, as this is the most cost-effective option.

    3.  **Intelligent Recovery (Spot Unavailability)**: When Spot is unavailable
        in the current region, the strategy employs a two-part recovery mechanism:
        a.  **Region Hopping**: If Spot has been down for a short period, it
            assumes the outage might be local and switches to a different region.
            The choice of the new region is based on historical data, prioritizing
            regions that have demonstrated higher Spot availability in the past.
            This prevents wasting time in a region with a prolonged outage.
        b.  **Adaptive Waiting**: For the current time step (while Spot is
            unavailable), it decides between waiting (ClusterType.NONE) or
            making progress with On-Demand. This decision is based on the
            current "slack" time. If there's ample slack, it waits to save
            costs. If the schedule is getting tighter, it uses On-Demand to
            avoid falling behind.
    """
    NAME = "AdaptiveHedgingStrategy"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initializes the solution from a spec file, setting up strategy
        parameters and state-tracking variables.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self.num_regions = self.env.get_num_regions()

        # Track historical spot availability with a neutral Bayesian prior.
        # Starting with (1 hit / 2 attempts) implies a 50% belief.
        self.region_spot_hits = [1.0] * self.num_regions
        self.region_spot_attempts = [2.0] * self.num_regions

        # Tracks consecutive time steps in the current region without spot.
        self.current_outage_streak = 0

        # --- Heuristic Parameters ---
        self.OUTAGE_STREAK_SWITCH_THRESHOLD = 1
        self.WAIT_SLACK_THRESHOLD_MULTIPLIER = 5.0
        self.PANIC_BUFFER_SECONDS = self.env.gap_seconds * 1.0

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decides the next action (cluster type and potential region switch)
        at each time step.
        """
        # Calculate current progress and time remaining.
        work_done = sum(self.task_done_time)
        work_remaining = self.task_duration - work_done

        if work_remaining <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        current_region = self.env.get_current_region()

        # Update historical statistics for the current region.
        self.region_spot_attempts[current_region] += 1.0
        if has_spot:
            self.region_spot_hits[current_region] += 1.0
            self.current_outage_streak = 0
        else:
            self.current_outage_streak += 1

        # Calculate the time needed to finish if we use On-Demand from now on.
        time_needed_on_demand = work_remaining + self.restart_overhead

        # 1. Panic Mode: If deadline is too close, use On-Demand to guarantee completion.
        if time_to_deadline <= time_needed_on_demand + self.PANIC_BUFFER_SECONDS:
            return ClusterType.ON_DEMAND

        # 2. Normal Mode: If spot is available, always use it.
        if has_spot:
            return ClusterType.SPOT

        # 3. Recovery Mode: Spot is unavailable.
        # 3a. Decide whether to switch regions for the next step.
        if self.num_regions > 1 and self.current_outage_streak >= self.OUTAGE_STREAK_SWITCH_THRESHOLD:
            candidate_regions = [
                (i, self.region_spot_hits[i] / self.region_spot_attempts[i])
                for i in range(self.num_regions) if i != current_region
            ]
            if candidate_regions:
                # Pick the region with the best historical spot success rate.
                best_region_idx, _ = max(candidate_regions, key=lambda item: item[1])
                self.env.switch_region(best_region_idx)
                self.current_outage_streak = 0  # Reset streak after switching.

        # 3b. Decide cluster type for the current step (where spot is down).
        safe_slack_time = time_to_deadline - time_needed_on_demand
        wait_threshold = self.WAIT_SLACK_THRESHOLD_MULTIPLIER * self.restart_overhead

        if safe_slack_time > wait_threshold:
            # If slack is plentiful, wait for spot to return (no cost).
            return ClusterType.NONE
        else:
            # If slack is tight, use On-Demand to make progress.
            return ClusterType.ON_DEMAND
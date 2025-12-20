import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    A multi-region scheduling strategy that balances cost and deadline adherence.

    The strategy operates on a simple but effective principle: be greedy with cost
    savings when time permits, but switch to a reliable, expensive option when
    the deadline is at risk.

    Core Logic:
    1.  **Default Action (Greedy)**: Prioritize using cheap SPOT instances to minimize
        cost. If a SPOT instance is available in the current region, it will be used.

    2.  **Spot Search**: If a SPOT instance is not available in the current region,
        the strategy will not immediately fall back to an expensive ON_DEMAND instance.
        Instead, it will cycle to the next available AWS region and wait for one
        timestep (by returning `ClusterType.NONE`). This action uses up slack time
        to search for cheaper resources across regions, avoiding unnecessary costs.

    3.  **Deadline-Aware Safety Net**: The cornerstone of the strategy is its
        "point of no return" calculation. At every step, it computes the
        worst-case time required to finish the remaining work using a reliable
        ON_DEMAND instance, including any potential restart overheads. If the time
        remaining until the deadline is less than or equal to this calculated
        worst-case time, the strategy enters a "danger zone". In this mode, it
        overrides all cost-saving measures and immediately selects `ClusterType.ON_DEMAND`
        to guarantee the job finishes on time.

    This two-tiered approach ensures that the strategy is as cost-effective as
    possible while robustly avoiding deadline failures.
    """

    NAME = "deadline_aware_greedy_cycler"

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
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
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        # --- Safety Net Calculation ---
        # Calculate the worst-case time required to finish the job using On-Demand
        # from this point forward, assuming a full restart overhead is incurred.
        
        # Timesteps needed for a potential restart overhead.
        num_overhead_steps = math.ceil(self.restart_overhead / self.env.gap_seconds)
        
        # Timesteps needed to complete the remaining work.
        num_work_steps = math.ceil(remaining_work / self.env.gap_seconds)
        
        # Total time needed from now if we switch to On-Demand.
        time_needed_for_od = (num_overhead_steps + num_work_steps) * self.env.gap_seconds
        
        time_left_to_deadline = self.deadline - self.env.elapsed_seconds

        # If time left is insufficient for the On-Demand fallback, we must
        # use On-Demand now to guarantee completion before the deadline.
        if time_left_to_deadline <= time_needed_for_od:
            return ClusterType.ON_DEMAND

        # --- Greedy Cost-Saving Logic ---
        # If not in the danger zone, we have slack time. Prioritize Spot.

        if has_spot:
            # A cheap Spot instance is available, so we use it.
            return ClusterType.SPOT
        else:
            # No Spot in the current region. Search for it in other regions.
            num_regions = self.env.get_num_regions()
            if num_regions > 1:
                # Cycle to the next region to check for spot availability
                # in the subsequent timestep.
                current_region = self.env.get_current_region()
                next_region = (current_region + 1) % num_regions
                self.env.switch_region(next_region)
            
            # Use no cluster for this step to avoid On-Demand costs while searching.
            return ClusterType.NONE

import json
from argparse import Namespace
import math

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    Your multi-region scheduling strategy.
    
    This strategy uses an Upper Confidence Bound (UCB1) algorithm to manage the
    exploration-exploitation trade-off between different AWS regions.
    
    Core Logic:
    1.  **Panic Mode:** If the deadline is approaching and there's not enough time
        to finish the job even with a 100% reliable On-Demand instance, the
        strategy will lock into using On-Demand to guarantee completion.
    2.  **Spot-First:** If Spot instances are available in the current region and
        the system is not in panic mode, it will always choose Spot to minimize cost.
    3.  **No Spot Available:** If Spot is unavailable, the strategy decides between:
        a. **Switching Region:** It uses a UCB1 score to evaluate other regions. The
           score balances known performance (exploitation) with uncertainty
           (exploration). If another region's score is significantly higher than
           the current region's historical performance, it switches.
        b. **Waiting:** If the current region has a historically high spot
           availability, it may choose to wait (return NONE), gambling that
           Spot will become available again soon. This avoids the cost of On-Demand.
        c. **Using On-Demand:** If no other region looks promising and the current
           region is historically unreliable, it falls back to On-Demand to ensure
           progress is made.
    """

    NAME = "ucb_strategy"

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

        self.initialized = False
        return self

    def _initialize_strategy(self):
        """Initializes strategy-specific state on the first simulation step."""
        self.num_regions = self.env.get_num_regions()
        
        self.region_stats = [
            {'samples': 0, 'value': 0.0} for _ in range(self.num_regions)
        ]
        self.total_steps = 0
        
        # --- Hyperparameters ---
        self.UCB_C = 1.0
        self.SWITCH_THRESHOLD = 0.15
        self.WAIT_THRESHOLD = 0.5
        self.OD_BUFFER_FACTOR = 1.2
        
        self.initialized = True

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._initialize_strategy()

        # 1. Update UCB statistics for the current region
        self.total_steps += 1
        current_region = self.env.get_current_region()
        stats = self.region_stats[current_region]
        current_availability = 1.0 if has_spot else 0.0

        stats['samples'] += 1
        stats['value'] += (current_availability - stats['value']) / stats['samples']

        # 2. Check for task completion
        work_done = sum(self.task_done_time)
        work_left = self.task_duration - work_done
        if work_left <= 0:
            return ClusterType.NONE

        # 3. PANIC MODE: Guarantee completion by switching to On-Demand if deadline is near
        time_left = self.deadline - self.env.elapsed_seconds
        time_needed_for_od = work_left + self.restart_overhead
        
        if time_left <= time_needed_for_od * self.OD_BUFFER_FACTOR:
            return ClusterType.ON_DEMAND

        # 4. Main Decision Logic
        if has_spot:
            return ClusterType.SPOT

        # If spot is NOT available...
        best_ucb_score = -1.0
        best_region_to_switch = -1

        for i in range(self.num_regions):
            if i == current_region:
                continue
            
            istats = self.region_stats[i]
            if istats['samples'] == 0:
                ucb_score = float('inf')
            else:
                exploitation = istats['value']
                exploration = self.UCB_C * math.sqrt(
                    math.log(self.total_steps + 1) / istats['samples']
                )
                ucb_score = exploitation + exploration
            
            if ucb_score > best_ucb_score:
                best_ucb_score = ucb_score
                best_region_to_switch = i

        current_region_value = self.region_stats[current_region]['value']

        if best_region_to_switch != -1 and best_ucb_score > current_region_value + self.SWITCH_THRESHOLD:
            self.env.switch_region(best_region_to_switch)
            return ClusterType.ON_DEMAND
        else:
            if current_region_value > self.WAIT_THRESHOLD:
                return ClusterType.NONE
            else:
                return ClusterType.ON_DEMAND
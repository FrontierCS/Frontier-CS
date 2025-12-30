import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

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

    def _initialize(self):
        """
        One-time initialization on the first call to _step.
        """
        self.num_regions = self.env.get_num_regions()
        
        # Hyperparameters for the strategy
        # Window size for calculating spot availability probability
        self.window_size = 12
        # Probability threshold to consider a region "promising" for a switch
        self.switch_proba_threshold = 0.75

        # State tracking for each region
        self.spot_history = [[] for _ in range(self.num_regions)]
        # Optimistic start: assume all regions have 100% spot availability
        self.spot_probas = [1.0] * self.num_regions
        
        self.initialized = True

    def _update_history(self, current_region: int, has_spot: bool):
        """
        Update the spot availability history and probability for the current region.
        """
        history = self.spot_history[current_region]
        history.append(1 if has_spot else 0)
        
        # Maintain a sliding window of history
        if len(history) > self.window_size:
            history.pop(0)
        
        # Recalculate the probability based on the updated history
        if history:
            self.spot_probas[current_region] = sum(history) / len(history)

    def _find_best_alternative_region(self, exclude_region: int):
        """
        Find the region with the highest historical spot availability, excluding
        the specified region.
        """
        best_region = None
        max_p = -1.0
        
        # Find the region with the max probability, breaking ties with lower index
        for i in range(self.num_regions):
            if i == exclude_region:
                continue
            
            if self.spot_probas[i] > max_p:
                max_p = self.spot_probas[i]
                best_region = i
                
        return best_region, max_p

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        if not self.initialized:
            self._initialize()

        current_region = self.env.get_current_region()
        self._update_history(current_region, has_spot)

        remaining_work = self.task_duration - sum(self.task_done_time)

        if remaining_work <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds

        # 1. CRITICAL / SAFETY NET
        # Time needed to finish on On-Demand including one potential restart and a buffer.
        critical_time_needed = remaining_work + self.restart_overhead + self.env.gap_seconds
        if time_to_deadline <= critical_time_needed:
            return ClusterType.ON_DEMAND

        # 2. HAPPY PATH
        # If spot is available and we are not in the critical zone, use it.
        if has_spot:
            return ClusterType.SPOT

        # At this point, has_spot is False.
        # 3. CAUTIOUS MODE
        # If slack is tight, use On-Demand to make guaranteed progress.
        # "Tight" means enough time for OD finish + one failed switch attempt.
        cautious_time_needed = critical_time_needed + self.restart_overhead
        if time_to_deadline <= cautious_time_needed:
            return ClusterType.ON_DEMAND

        # 4. ADVENTUROUS MODE
        # We have plenty of slack. Let's try to find a region with spot.
        best_alt_region, max_proba = self._find_best_alternative_region(exclude_region=current_region)
        
        current_region_proba = self.spot_probas[current_region]

        # Condition to switch: there is a promising alternative region which is
        # historically better than the current one.
        if (best_alt_region is not None and 
            max_proba > self.switch_proba_threshold and
            max_proba > current_region_proba):
            
            self.env.switch_region(best_alt_region)
            # After switching, we pause (NONE) to observe the new region's status
            # while minimizing cost.
            return ClusterType.NONE
        else:
            # No promising region to switch to. Since we have plenty of slack,
            # we wait (NONE) for spot to hopefully reappear.
            return ClusterType.NONE
import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "Cant-Be-Late_Strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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
        # 1. Calculate current state variables
        work_done = sum(self.task_done_time)
        remaining_work = self.task_duration - work_done

        # If the task is finished, do nothing to save cost.
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        gap = self.env.gap_seconds

        # If already past the deadline, stop incurring costs.
        if time_to_deadline < 0:
            return ClusterType.NONE

        # 2. Determine if we are in "panic mode"
        if gap > 0:
            n_steps_work = math.ceil(remaining_work / gap)
        else:
            n_steps_work = float('inf') if remaining_work > 0 else 0

        # Time required to finish if we switch to On-Demand now, assuming the
        # switch costs one timestep of progress.
        time_needed_for_od_finish = (1 + n_steps_work) * gap

        # A safety buffer to absorb one failure (e.g., a Spot preemption or a
        # failed region-hop). A failure costs one timestep.
        safety_buffer = gap
        
        # The panic threshold is the time needed to finish on OD plus the safety buffer.
        # If time to deadline is less than this, we can't risk a failure.
        panic_threshold = time_needed_for_od_finish + safety_buffer

        is_panic_mode = time_to_deadline < panic_threshold

        # 3. Choose action based on mode
        if is_panic_mode:
            # Not enough slack to risk a failure. Must use the reliable On-Demand
            # option to guarantee completion.
            return ClusterType.ON_DEMAND
        else:
            # We have enough slack time, so prioritize low cost.
            if has_spot:
                # Best case: cheap Spot resource is available.
                return ClusterType.SPOT
            else:
                # No Spot in the current region.
                num_regions = self.env.get_num_regions()
                if num_regions > 1:
                    # Gamble on finding a Spot instance in another region.
                    current_region = self.env.get_current_region()
                    next_region = (current_region + 1) % num_regions
                    self.env.switch_region(next_region)
                    
                    # Switching forces a restart, so no work is done this step.
                    # Return NONE to avoid paying for an unused instance.
                    return ClusterType.NONE
                else:
                    # Only one region and no Spot. Nowhere else to look.
                    # Since we are not in panic mode, we can afford to wait.
                    # The panic logic will eventually force a switch to On-Demand
                    # if Spot availability does not resume.
                    return ClusterType.NONE

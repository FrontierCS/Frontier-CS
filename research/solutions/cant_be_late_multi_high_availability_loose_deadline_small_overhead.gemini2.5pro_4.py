import json
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """
    An adaptive multi-region scheduling strategy that balances cost and deadline adherence.
    """

    NAME = "adaptive_slack_v1"

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

        self.num_regions = len(config.get("trace_files", []))
        if self.num_regions == 0:
            self.num_regions = 1 

        self.region_stats = [
            {'spot_seen': 0, 'total_seen': 0, 'consecutive_outages': 0}
            for _ in range(self.num_regions)
        ]

        # --- Hyperparameters ---
        self.INITIAL_SAFETY_MARGIN = 1.15
        self.FINAL_SAFETY_MARGIN = 1.01
        self.CONSECUTIVE_OUTAGE_THRESHOLD = 2
        self.WAIT_SLACK_THRESHOLD_FACTOR = 0.25

        # --- Calculated Parameters ---
        initial_slack = self.deadline - self.task_duration
        self.wait_slack_threshold_sec = initial_slack * self.WAIT_SLACK_THRESHOLD_FACTOR

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # --- 0. State Update and Pre-computation ---
        env_num_regions = self.env.get_num_regions()
        if env_num_regions > len(self.region_stats):
             self.region_stats.extend([
                {'spot_seen': 0, 'total_seen': 0, 'consecutive_outages': 0}
                for _ in range(env_num_regions - len(self.region_stats))
            ])
             self.num_regions = env_num_regions

        current_region = self.env.get_current_region()
        
        stats = self.region_stats[current_region]
        stats['total_seen'] += 1
        if has_spot:
            stats['spot_seen'] += 1
            stats['consecutive_outages'] = 0
        else:
            stats['consecutive_outages'] += 1

        work_done = sum(self.task_done_time)
        work_rem = self.task_duration - work_done

        if work_rem <= 0:
            return ClusterType.NONE

        time_to_deadline = self.deadline - self.env.elapsed_seconds
        gap_seconds = self.env.gap_seconds

        # --- 1. Urgency Calculation (Panic Mode) ---
        work_plus_overhead = work_rem + self.restart_overhead
        
        if gap_seconds <= 0:
             return ClusterType.ON_DEMAND
             
        steps_needed_od = math.ceil(work_plus_overhead / gap_seconds)
        time_needed_od = steps_needed_od * gap_seconds

        progress_ratio = min(1.0, work_done / self.task_duration) if self.task_duration > 0 else 1.0
        safety_margin = self.INITIAL_SAFETY_MARGIN - (self.INITIAL_SAFETY_MARGIN - self.FINAL_SAFETY_MARGIN) * progress_ratio
        
        if time_needed_od * safety_margin >= time_to_deadline:
            return ClusterType.ON_DEMAND

        # --- 2. Normal Mode (Sufficient Slack) ---
        if has_spot:
            return ClusterType.SPOT

        # --- Spot is unavailable. Decide whether to switch, use OD, or wait. ---

        # 2a. Evaluate Region Switching
        if stats['consecutive_outages'] >= self.CONSECUTIVE_OUTAGE_THRESHOLD:
            
            def get_region_score(r_idx):
                r_stats = self.region_stats[r_idx]
                return (r_stats['spot_seen'] + 1) / (r_stats['total_seen'] + 2)

            current_score = get_region_score(current_region)
            
            best_alt_region = -1
            max_alt_score = -1.0
            
            for i in range(self.num_regions):
                if i == current_region:
                    continue
                
                score = get_region_score(i)
                if score > max_alt_score:
                    max_alt_score = score
                    best_alt_region = i
            
            if best_alt_region != -1 and max_alt_score > current_score:
                self.env.switch_region(best_alt_region)
                return ClusterType.ON_DEMAND

        # 2b. Stay in Region: On-Demand vs. Wait (None)
        slack_sec = time_to_deadline - time_needed_od
        
        if slack_sec > self.wait_slack_threshold_sec:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND
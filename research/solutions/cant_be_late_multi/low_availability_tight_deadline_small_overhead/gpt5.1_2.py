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

        # Core parameters (in seconds); fall back to config-derived values if base class
        # does not define them for some reason.
        self.task_duration = getattr(
            self, "task_duration", float(config["duration"]) * 3600.0
        )
        self.deadline = getattr(
            self, "deadline", float(config["deadline"]) * 3600.0
        )
        self.restart_overhead = getattr(
            self, "restart_overhead", float(config["overhead"]) * 3600.0
        )

        # Time step size.
        self.gap_seconds = getattr(self.env, "gap_seconds", 60.0)

        # Progress tracking (avoid summing the whole list every step).
        self.progress_done = 0.0
        self.last_task_segments_len = 0

        # Commitment to on-demand: once True, we never go back to Spot.
        self.committed_to_od = False

        # Region-related state.
        try:
            self.num_regions = self.env.get_num_regions()
        except Exception:
            self.num_regions = 1

        self.region_spot_steps = [0] * self.num_regions
        self.region_total_steps = [0] * self.num_regions

        self.no_spot_counter = 0
        self.steps_since_last_switch = 0

        # Exploration window: allow region switching only in the earlier part of the run.
        slack = max(0.0, self.deadline - self.task_duration)
        if slack > 0.0:
            self.exploration_limit_seconds = min(self.deadline * 0.3, slack * 0.7)
        else:
            self.exploration_limit_seconds = 0.0

        # Helper to convert a time duration to step counts.
        gap = self.gap_seconds

        def to_steps(seconds: float, min_steps: int = 1) -> int:
            if gap <= 0:
                return min_steps
            steps = int(round(seconds / gap))
            if steps < min_steps:
                steps = min_steps
            return steps

        # Region-switching parameters.
        # Switch after about 15 minutes of no spot, with a cooldown of ~30 minutes.
        self.no_spot_threshold_steps = to_steps(15 * 60, 1)
        self.switch_cooldown_steps = to_steps(30 * 60, 1)

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        # Incremental update of completed work.
        segs = self.task_done_time
        last_len = self.last_task_segments_len
        cur_len = len(segs)
        if cur_len > last_len:
            total = self.progress_done
            for i in range(last_len, cur_len):
                total += segs[i]
            self.progress_done = total
            self.last_task_segments_len = cur_len

        remaining_work = self.task_duration - self.progress_done
        if remaining_work <= 0.0:
            # Task already finished.
            self.committed_to_od = True
            return ClusterType.NONE

        env = self.env
        elapsed = env.elapsed_seconds
        time_left = self.deadline - elapsed
        if time_left <= 0.0:
            # Deadline passed (should rarely happen); run on-demand to minimize penalty.
            self.committed_to_od = True
            return ClusterType.ON_DEMAND

        gap = self.gap_seconds

        # Decide whether to irrevocably commit to On-Demand.
        if not self.committed_to_od:
            # If we no longer have enough slack to afford losing another full step
            # plus a restart overhead before finishing the remaining work on On-Demand,
            # commit now.
            if time_left <= self.restart_overhead + remaining_work + gap:
                self.committed_to_od = True

        if self.committed_to_od:
            # From this point on, always use On-Demand; never switch regions.
            return ClusterType.ON_DEMAND

        # Pre-commit phase: we use Spot when available; otherwise we may idle and
        # optionally switch regions to chase better Spot availability.

        # Update region stats with current observation.
        if self.num_regions > 0:
            current_region = env.get_current_region()
        else:
            current_region = 0

        if self.num_regions > 0:
            self.region_total_steps[current_region] += 1
            if has_spot:
                self.region_spot_steps[current_region] += 1

        # If Spot is available, always use it before commitment.
        if has_spot:
            self.no_spot_counter = 0
            self.steps_since_last_switch += 1
            return ClusterType.SPOT

        # Spot not available in the current region.
        self.no_spot_counter += 1
        self.steps_since_last_switch += 1

        # Region switching logic (only during exploration window, before OD commit).
        if (
            self.num_regions > 1
            and elapsed < self.exploration_limit_seconds
            and self.no_spot_counter >= self.no_spot_threshold_steps
            and self.steps_since_last_switch >= self.switch_cooldown_steps
        ):
            best_region = current_region
            best_score = -1.0
            for r in range(self.num_regions):
                if r == current_region:
                    continue
                total = self.region_total_steps[r]
                spot = self.region_spot_steps[r]
                # Use a Beta(1,1) prior -> unseen regions start with score 0.5.
                score = (spot + 1.0) / (total + 2.0)
                if score > best_score:
                    best_score = score
                    best_region = r
            if best_region != current_region:
                env.switch_region(best_region)
                self.steps_since_last_switch = 0
                self.no_spot_counter = 0

        # Idle (no cost) while waiting for Spot or until we must commit to On-Demand.
        return ClusterType.NONE
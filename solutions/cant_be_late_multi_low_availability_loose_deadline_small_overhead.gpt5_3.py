import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_mr_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Runtime state (initialized lazily in _step when env is ready)
        self._initialized = False
        self._commit_to_od = False
        self._cooldown_remaining = 0
        self._alpha_prior = 2.0
        self._switch_delta = 0.06
        self._down_streak_threshold = 2
        self._cooldown_steps = 1

        return self

    def _lazy_init(self):
        if self._initialized:
            return
        n = self.env.get_num_regions()
        self._region_seen = [0] * n
        self._region_up = [0] * n
        self._region_down_streak = [0] * n
        self._initialized = True

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        self._region_seen[region_idx] += 1
        if has_spot:
            self._region_up[region_idx] += 1
            self._region_down_streak[region_idx] = 0
        else:
            self._region_down_streak[region_idx] += 1

    def _region_score(self, idx: int) -> float:
        # Beta prior smoothed estimate; penalize down streak slightly to encourage switching
        seen = self._region_seen[idx]
        up = self._region_up[idx]
        alpha = self._alpha_prior
        base = (up + alpha) / (seen + 2 * alpha) if seen >= 0 else 0.5
        penalty = 0.03 * min(self._region_down_streak[idx], 10)
        s = base - penalty
        if s < 0.0:
            s = 0.0
        if s > 1.0:
            s = 1.0
        return s

    def _best_region(self):
        n = self.env.get_num_regions()
        best_idx = 0
        best_score = self._region_score(0)
        for i in range(1, n):
            s = self._region_score(i)
            if s > best_score:
                best_score = s
                best_idx = i
        return best_idx, best_score

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Decrement cooldown
        if self._cooldown_remaining > 0:
            self._cooldown_remaining -= 1

        current_region = self.env.get_current_region()
        # Update stats with current observation
        self._update_region_stats(current_region, has_spot)

        # Remaining work and time
        work_done = sum(self.task_done_time)
        remaining_work = max(0.0, self.task_duration - work_done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        # Safe commit computation: enough time to finish with OD if we start now
        od_time_needed = remaining_work + self.restart_overhead

        # Margin to guard discretization and pending overheads
        commit_margin = max(self.env.gap_seconds, 0.5 * self.restart_overhead)

        # If already committed, keep using OD
        if self._commit_to_od:
            return ClusterType.ON_DEMAND

        # If close to deadline, commit to OD
        if time_left <= od_time_needed + commit_margin:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Opportunistic Spot usage when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available in current region; decide to wait or switch or commit early
        # Pre-commit slightly earlier if very close to barrier (two steps margin)
        if time_left <= od_time_needed + 2.0 * self.env.gap_seconds:
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Consider switching regions to one with better estimated availability
        n_regions = self.env.get_num_regions()
        if n_regions > 1:
            current_score = self._region_score(current_region)
            best_idx, best_score = self._best_region()

            should_switch = False
            if best_idx != current_region:
                # Switch if the other region appears significantly better or we are in a down streak
                if (best_score - current_score) >= self._switch_delta:
                    should_switch = True
                elif self._region_down_streak[current_region] >= self._down_streak_threshold:
                    should_switch = True

            if should_switch and self._cooldown_remaining <= 0:
                self.env.switch_region(best_idx)
                self._cooldown_remaining = self._cooldown_steps
                # Wait this step; we'll try spot next step in the new region
                return ClusterType.NONE

            # Optional exploration: mild round-robin if severe down streak and no clear best
            if (
                self._region_down_streak[current_region] >= (self._down_streak_threshold + 2)
                and self._cooldown_remaining <= 0
            ):
                next_idx = (current_region + 1) % n_regions
                self.env.switch_region(next_idx)
                self._cooldown_remaining = self._cooldown_steps
                return ClusterType.NONE

        # Default: wait for Spot to return
        return ClusterType.NONE

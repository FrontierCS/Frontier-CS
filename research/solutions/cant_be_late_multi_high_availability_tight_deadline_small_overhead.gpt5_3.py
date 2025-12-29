import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cantbe_late_mr_ewma_v1"

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

        # Strategy state (initialized lazily in _step when env is ready)
        self._initialized = False
        return self

    def _lazy_init(self):
        if self._initialized:
            return
        # Regions
        try:
            num_regions = self.env.get_num_regions()
        except Exception:
            num_regions = 1
        self._num_regions = max(1, int(num_regions))

        # EWMA for spot availability per region
        self._ewma = [0.7] * self._num_regions  # optimistic prior given high availability
        self._ewma_alpha = 0.08  # smoothing factor

        # Counts (for optional diagnostics/adaptation)
        self._obs = [0] * self._num_regions
        self._succ = [0] * self._num_regions

        # Streak of consecutive steps without spot in current region
        self._no_spot_streak = 0

        # Safety margin in seconds: switch to OD when slack <= margin
        # Choose conservatively: 2 steps or at least 4x overhead, at most 3 hours
        gap = float(self.env.gap_seconds)
        overhead = float(self.restart_overhead)
        self._safety_margin_seconds = max(4.0 * overhead, min(2.5 * gap, 3.0 * 3600.0))

        # Region switching parameters
        self._switch_threshold = 0.05  # min EWMA advantage to switch
        self._probe_offset = 1  # for round-robin probing when uncertain

        # Once set, we commit to OD until finish
        self._od_lock = False

        self._initialized = True

    def _update_region_stats(self, region_idx: int, has_spot: bool):
        # Update EWMA and counts based on observation in the given region
        self._obs[region_idx] += 1
        if has_spot:
            self._succ[region_idx] += 1
        alpha = self._ewma_alpha
        old = self._ewma[region_idx]
        self._ewma[region_idx] = (1.0 - alpha) * old + alpha * (1.0 if has_spot else 0.0)

    def _select_region_on_no_spot(self, current_region: int) -> int:
        # Choose best region by EWMA if clearly better; otherwise probe next region
        best_idx = current_region
        best_score = self._ewma[current_region]
        for i in range(self._num_regions):
            if self._ewma[i] > best_score:
                best_score = self._ewma[i]
                best_idx = i

        if best_idx != current_region and (best_score - self._ewma[current_region]) > self._switch_threshold:
            return best_idx

        # No clear winner: probe next region in round-robin manner to collect data
        # Stagger probing based on streak count to avoid rapid toggling between two regions
        next_idx = (current_region + max(1, min(self._no_spot_streak, self._num_regions - 1))) % self._num_regions
        return next_idx if next_idx != current_region else (current_region + self._probe_offset) % self._num_regions

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Snapshot current region before any switch (observation applies to this region)
        current_region = self.env.get_current_region()

        # Update region statistics with current observation
        self._update_region_stats(current_region, has_spot)

        # Compute remaining work and time
        done_work = float(sum(self.task_done_time))
        remain_work = max(0.0, float(self.task_duration) - done_work)
        remain_time = max(0.0, float(self.deadline) - float(self.env.elapsed_seconds))

        # If we've already finished, choose NONE to avoid cost (environment should stop soon)
        if remain_work <= 0.0:
            return ClusterType.NONE

        # Calculate slack
        slack = remain_time - remain_work

        # Lock to OD if we are too close to the deadline
        if not self._od_lock and slack <= self._safety_margin_seconds:
            self._od_lock = True

        # If locked, always run on OD
        if self._od_lock:
            # No need to switch region when on OD
            self._no_spot_streak = 0
            return ClusterType.ON_DEMAND

        # Not locked: prefer SPOT when available; otherwise pause (NONE) and possibly switch region
        if has_spot:
            self._no_spot_streak = 0
            return ClusterType.SPOT

        # No spot this step: pause to save cost, and pick a better region for the next step
        self._no_spot_streak += 1
        target_region = self._select_region_on_no_spot(current_region)
        if target_region != current_region:
            self.env.switch_region(target_region)

        return ClusterType.NONE
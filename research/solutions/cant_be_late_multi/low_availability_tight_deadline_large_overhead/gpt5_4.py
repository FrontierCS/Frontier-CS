import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_rr"

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

        # Strategy state
        self._initialized = False
        self._commit_to_od = False
        self._recency_window_seconds = None
        self._last_true_ts = None  # per-region last observed spot-true timestamp
        self._rr_next = 0
        self._commit_margin = None
        return self

    def _init_once(self):
        if self._initialized:
            return
        num_regions = self.env.get_num_regions()
        self._last_true_ts = [-1.0] * num_regions
        self._rr_next = self.env.get_current_region()
        # Recency window: prefer regions with spot observed within this window
        # Choose 6 hours as a heuristic window
        self._recency_window_seconds = 6.0 * 3600.0
        # Commit margin: one step worth of time as a safety buffer
        self._commit_margin = max(self.env.gap_seconds, 60.0)
        self._initialized = True

    def _update_region_stats(self, has_spot: bool):
        # Update last-seen timestamp for spot in current region
        if has_spot:
            idx = self.env.get_current_region()
            self._last_true_ts[idx] = self.env.elapsed_seconds

    def _should_commit_to_od(self, last_cluster_type: ClusterType) -> bool:
        # Remaining work and time
        work_done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining_work = max(0.0, self.task_duration - work_done)
        remaining_time = max(0.0, self.deadline - self.env.elapsed_seconds)

        # If already committed, keep it
        if self._commit_to_od:
            return True

        # If already on OD and we keep running it, no new overhead
        overhead_needed = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead

        # Commit to OD if not enough slack to wait for spot
        # Safety buffer adds one step to account for discretization/overheads within step
        return remaining_time <= (remaining_work + overhead_needed + self._commit_margin)

    def _choose_region_when_waiting(self):
        # Prefer the region with the most recent spot observation within the recency window.
        now = self.env.elapsed_seconds
        current = self.env.get_current_region()
        num_regions = self.env.get_num_regions()

        # Candidates within recency window excluding current region
        best_idx = -1
        best_ts = -1.0
        window = self._recency_window_seconds
        for i in range(num_regions):
            if i == current:
                continue
            ts = self._last_true_ts[i]
            if ts >= 0.0 and (now - ts) <= window:
                if ts > best_ts:
                    best_ts = ts
                    best_idx = i

        if best_idx != -1:
            target = best_idx
        else:
            # Round-robin to diversify search
            target = (current + 1) % num_regions

        if target != current:
            self.env.switch_region(target)

        # Update next RR base
        self._rr_next = (target + 1) % num_regions

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_once()
        self._update_region_stats(has_spot)

        # If we must commit to OD to guarantee deadline, do it and never switch back
        if self._should_commit_to_od(last_cluster_type):
            self._commit_to_od = True
            return ClusterType.ON_DEMAND

        # Not committed to OD: prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available here; still have slack.
        # Proactively search other regions by switching while idling.
        self._choose_region_when_waiting()
        return ClusterType.NONE
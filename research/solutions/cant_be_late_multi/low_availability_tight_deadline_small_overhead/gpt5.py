import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "safe_od_spot_guard_v5"

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

        # Lazy init for env-dependent fields in _step
        self._mr_init_done = False
        self._od_committed = False
        self._last_td_len = 0
        self._acc_work_done = 0.0
        return self

    def _lazy_init(self):
        if self._mr_init_done:
            return
        # Initialize per-region stats
        try:
            n = self.env.get_num_regions()
        except Exception:
            n = 1
        self._n_regions = max(1, int(n))
        self._avail_count = [0] * self._n_regions
        self._seen_count = [0] * self._n_regions
        self._consec_unavail = [0] * self._n_regions
        self._last_switch_step = -1
        self._mr_init_done = True

    def _update_work_done_acc(self):
        # Incrementally maintain sum(self.task_done_time) to O(1) amortized per step
        td_list = self.task_done_time
        if not isinstance(td_list, list):
            # Fallback: compute directly
            return sum(td_list)
        n = len(td_list)
        if n > self._last_td_len:
            # Add only new segments
            add_sum = 0.0
            for i in range(self._last_td_len, n):
                add_sum += float(td_list[i])
            self._acc_work_done += add_sum
            self._last_td_len = n
        return self._acc_work_done

    def _select_best_region(self, current_region: int) -> int:
        # Choose region with highest smoothed availability ratio
        # Laplace smoothing to handle zeros
        best_idx = current_region
        best_score = -1.0
        for i in range(self._n_regions):
            seen = self._seen_count[i]
            avail = self._avail_count[i]
            score = (avail + 1.0) / (seen + 2.0)
            # Slight penalty for consecutive unavailability
            score *= 1.0 / (1.0 + 0.1 * self._consec_unavail[i])
            if score > best_score + 1e-12 or (abs(score - best_score) <= 1e-12 and i != current_region and self._consec_unavail[i] < self._consec_unavail[best_idx]):
                best_score = score
                best_idx = i
        return best_idx

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # Update work done efficiently
        work_done = self._update_work_done_acc()

        # Remaining work and time to deadline
        remaining_work = max(0.0, self.task_duration - work_done)
        time_left = max(0.0, self.deadline - self.env.elapsed_seconds)

        # Early exit: if no remaining work (environment may still call), choose NONE
        if remaining_work <= 0.0:
            return ClusterType.NONE

        # Update per-region spot availability stats with observation at current region
        cur_region = 0
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if 0 <= cur_region < self._n_regions:
            self._seen_count[cur_region] += 1
            if has_spot:
                self._avail_count[cur_region] += 1
                self._consec_unavail[cur_region] = 0
            else:
                self._consec_unavail[cur_region] += 1

        # Determine OD overhead if we commit to OD now
        # If already on OD and no pending overhead -> 0; else restart_overhead
        od_overhead_now = 0.0
        if last_cluster_type == ClusterType.ON_DEMAND and (getattr(self, "remaining_restart_overhead", 0.0) or 0.0) <= 1e-9:
            od_overhead_now = 0.0
        else:
            od_overhead_now = self.restart_overhead

        # Safety margin if we wait/try one more step before committing to OD
        # After one more step we might need to pay OD overhead if currently 0.
        gap = self.env.gap_seconds
        margin = gap + max(0.0, self.restart_overhead - od_overhead_now)

        # If we have little time left, commit to OD
        if self._od_committed or time_left <= remaining_work + od_overhead_now + margin:
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Before committing, prefer SPOT if available
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available in current region and not yet committed to OD.
        # Use slack to wait and optionally switch to a better region for next step.
        # Switch region to one with highest estimated spot availability; return NONE to avoid invalid SPOT return.
        next_region = self._select_best_region(cur_region)
        if next_region != cur_region and self._n_regions > 1:
            try:
                self.env.switch_region(next_region)
            except Exception:
                pass

        # Wait this step to preserve budget and try for future SPOT (or until OD commit threshold triggers)
        return ClusterType.NONE
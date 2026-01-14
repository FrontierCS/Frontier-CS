import json
from argparse import Namespace
from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "deadline_rr_od_guard"

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
        # Internal state
        self._initialized = False
        self._cached_done_sum = 0.0
        self._last_task_done_len = 0
        self._step_counter = 0
        self._num_regions = 1
        self._rr_next = 0
        return self

    def _initialize_runtime(self):
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        # Start round-robin pointer at next region after current
        try:
            cur = int(self.env.get_current_region())
        except Exception:
            cur = 0
        self._rr_next = (cur + 1) % max(self._num_regions, 1)
        self._initialized = True

    def _update_work_done_cache(self):
        # Incrementally update cached sum of task_done_time to avoid O(n) sums each step
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_done_len:
            # Usually only one new segment per step
            for i in range(self._last_task_done_len, cur_len):
                self._cached_done_sum += float(self.task_done_time[i])
            self._last_task_done_len = cur_len

    def _should_force_on_demand_now(self, last_cluster_type, remaining_work, time_left):
        # If we switch to OD now, how much time do we need?
        # If already on OD, no switch overhead; else include one restart overhead.
        overhead_to_switch = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else self.restart_overhead
        return time_left <= remaining_work + overhead_to_switch + 1e-6

    def _can_afford_to_wait_one_step(self, remaining_work, time_left):
        # If we wait one step (return NONE), can we still finish by switching to OD next step?
        # We assume we'll pay one restart overhead when switching to OD (worst-case safety).
        # To be safe, require time_left after waiting gap to be >= remaining_work + restart_overhead
        # i.e., time_left - gap >= remaining_work + restart_overhead
        return (time_left - self.env.gap_seconds) >= (remaining_work + self.restart_overhead)

    def _pick_next_region_round_robin(self):
        if self._num_regions <= 1:
            return 0
        cur = self.env.get_current_region()
        target = self._rr_next
        if target == cur:
            target = (target + 1) % self._num_regions
        self._rr_next = (target + 1) % self._num_regions
        return target

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if not self._initialized:
            self._initialize_runtime()
        self._step_counter += 1

        # Update cached work done
        self._update_work_done_cache()

        # Compute times
        remaining_work = max(0.0, self.task_duration - self._cached_done_sum)
        time_left = self.deadline - self.env.elapsed_seconds

        # If already done or no time left, do nothing
        if remaining_work <= 0.0 or time_left <= 0.0:
            return ClusterType.NONE

        # If we must ensure completion now via OD
        if self._should_force_on_demand_now(last_cluster_type, remaining_work, time_left):
            return ClusterType.ON_DEMAND

        # Prefer Spot if available and not in forced OD window
        if has_spot:
            return ClusterType.SPOT

        # Spot not available in current region. Decide to wait/switch or use OD.
        # If we can afford to wait one step (and possibly switch region), do so; else fallback to OD.
        if self._can_afford_to_wait_one_step(remaining_work, time_left):
            # Attempt to switch to another region and probe next step
            if self._num_regions > 1:
                target = self._pick_next_region_round_robin()
                try:
                    self.env.switch_region(target)
                except Exception:
                    pass  # Best-effort; if switch unsupported, just wait in place
            return ClusterType.NONE

        # Not enough slack to wait; use OD now to guarantee completion.
        return ClusterType.ON_DEMAND
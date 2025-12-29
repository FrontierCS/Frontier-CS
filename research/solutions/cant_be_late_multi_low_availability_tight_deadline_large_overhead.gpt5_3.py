import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_jit_rr"

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

        # Lazy init states; will be finalized in first _step call since env might not be ready here
        self._initialized = False
        self._od_lock = False
        self._last_task_segments_len = 0
        self._task_done_sum = 0.0
        return self

    def _lazy_init(self):
        if self._initialized:
            return
        self._initialized = True
        # Number of regions
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        # Round-robin pointer initialized to current region
        try:
            self._rr_next = int(self.env.get_current_region())
        except Exception:
            self._rr_next = 0
        # Safety buffer in seconds for deadline guard
        # Use a moderate buffer to ensure finishing despite discretization and overhead nuances.
        gap = float(self.env.gap_seconds)
        # 0.25 step + 0.5*overhead (capped at 30 minutes)
        buffer = 0.25 * gap + 0.5 * float(self.restart_overhead)
        self._deadline_buffer = min(buffer, 1800.0)

        # Initialize progress sum
        self._last_task_segments_len = len(self.task_done_time)
        self._task_done_sum = float(sum(self.task_done_time)) if self._last_task_segments_len > 0 else 0.0

    def _update_progress_sum(self):
        # Efficiently maintain cumulative sum of task_done_time
        curr_len = len(self.task_done_time)
        if curr_len == self._last_task_segments_len:
            return
        if curr_len > self._last_task_segments_len:
            # Sum only new segments
            new_sum = 0.0
            for x in self.task_done_time[self._last_task_segments_len:]:
                new_sum += float(x)
            self._task_done_sum += new_sum
        else:
            # Unexpected (list reset); recompute to be safe
            self._task_done_sum = float(sum(self.task_done_time))
        self._last_task_segments_len = curr_len

    def _should_fallback_to_od(self) -> bool:
        # Compute if we must switch to OD to meet deadline
        now = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - now
        # Remaining work in seconds
        self._update_progress_sum()
        remaining_work = max(0.0, float(self.task_duration) - self._task_done_sum)

        # If already on OD and committed, we will not pay any new overhead
        if self._od_lock or self.env.cluster_type == ClusterType.ON_DEMAND:
            overhead_once = 0.0
        else:
            # Conservative: pay at least restart_overhead once we start OD
            rro = float(getattr(self, "remaining_restart_overhead", 0.0))
            # remaining_restart_overhead is also accessible from env
            try:
                rro = float(self.env.remaining_restart_overhead)
            except Exception:
                pass
            overhead_once = max(float(self.restart_overhead), rro)

        # If there isn't enough time left to finish using OD (considering a single overhead + buffer), fallback to OD now
        need_time = overhead_once + remaining_work + self._deadline_buffer
        return time_left <= need_time + 1e-6

    def _rotate_region(self):
        if self._num_regions <= 1:
            return
        cur = 0
        try:
            cur = int(self.env.get_current_region())
        except Exception:
            pass
        nxt = (cur + 1) % self._num_regions
        try:
            self.env.switch_region(nxt)
        except Exception:
            pass
        self._rr_next = nxt

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()

        # If we've already committed to OD, always continue on OD.
        if self._od_lock:
            return ClusterType.ON_DEMAND

        # Deadline guard: must ensure timely completion
        if self._should_fallback_to_od():
            self._od_lock = True
            return ClusterType.ON_DEMAND

        # Prefer SPOT if available
        if has_spot:
            return ClusterType.SPOT

        # Otherwise wait (NONE) and explore another region via round-robin to increase chance of finding SPOT
        self._rotate_region()
        return ClusterType.NONE
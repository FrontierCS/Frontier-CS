import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

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
        self._initialized = False
        return self

    def _ensure_state_initialized(self):
        env = self.env

        # Initialize at first call or when environment resets (elapsed_seconds decreases)
        if getattr(self, "_initialized", False):
            last_elapsed = getattr(self, "_last_elapsed", None)
            if last_elapsed is not None and env.elapsed_seconds >= last_elapsed:
                return

        # Number of regions
        num_regions = 1
        try:
            num_regions = env.get_num_regions()
        except Exception:
            pass
        if not isinstance(num_regions, int) or num_regions <= 0:
            num_regions = 1
        self._num_regions = num_regions

        # Core parameters (seconds)
        td_raw = getattr(self, "task_duration", None)
        if isinstance(td_raw, (list, tuple)):
            self._task_duration_s = float(td_raw[0]) if td_raw else 0.0
        elif td_raw is None:
            self._task_duration_s = 0.0
        else:
            self._task_duration_s = float(td_raw)

        ro_raw = getattr(self, "restart_overhead", None)
        if isinstance(ro_raw, (list, tuple)):
            self._restart_overhead_s = float(ro_raw[0]) if ro_raw else 0.0
        elif ro_raw is None:
            self._restart_overhead_s = 0.0
        else:
            self._restart_overhead_s = float(ro_raw)

        dl_raw = getattr(self, "deadline", None)
        if isinstance(dl_raw, (list, tuple)):
            self._deadline_s = float(dl_raw[0]) if dl_raw else 0.0
        elif dl_raw is None:
            self._deadline_s = 0.0
        else:
            self._deadline_s = float(dl_raw)

        # Commit flag: once True, we always use On-Demand
        self._use_on_demand = False

        # Cached progress
        td_list = getattr(self, "task_done_time", None)
        if isinstance(td_list, list):
            self._cached_done = float(sum(td_list)) if td_list else 0.0
            self._last_task_done_len = len(td_list)
        else:
            self._cached_done = 0.0
            self._last_task_done_len = 0

        # Safety margin before deadline to switch to On-Demand
        gap = getattr(env, "gap_seconds", 60.0)
        try:
            gap = float(gap)
        except Exception:
            gap = 60.0
        # At least one hour or two time steps, whichever larger
        self._commit_margin_s = max(2.0 * gap, 3600.0)

        self._initialized = True
        self._last_elapsed = env.elapsed_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = self.env
        self._ensure_state_initialized()

        # Update cached progress using only new segments
        td_list = self.task_done_time
        cur_len = len(td_list)
        if cur_len > self._last_task_done_len:
            new_segments = td_list[self._last_task_done_len:cur_len]
            self._cached_done += float(sum(new_segments))
            self._last_task_done_len = cur_len

        self._last_elapsed = env.elapsed_seconds

        # Remaining required work
        remaining_work = self._task_duration_s - self._cached_done
        if remaining_work <= 0.0:
            # Task already completed
            self._use_on_demand = True
            return ClusterType.NONE

        # Decide whether we must commit to On-Demand to meet the deadline
        if not self._use_on_demand:
            time_left = self._deadline_s - env.elapsed_seconds
            # Worst-case time needed if we switch to On-Demand now
            worst_needed = self._restart_overhead_s + remaining_work + self._commit_margin_s
            if time_left <= worst_needed:
                self._use_on_demand = True

        # Once committed, always use On-Demand for the rest of the episode
        if self._use_on_demand:
            return ClusterType.ON_DEMAND

        # Before commit: prefer Spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable in current region and not yet committed:
        # explore another region while idling (no cost, preserves deadline slack)
        try:
            cur_region = env.get_current_region()
        except Exception:
            cur_region = 0

        num_regions = getattr(self, "_num_regions", 1)
        if num_regions > 1:
            try:
                next_region = (int(cur_region) + 1) % num_regions
                if hasattr(env, "switch_region") and next_region != cur_region:
                    env.switch_region(next_region)
            except Exception:
                pass

        return ClusterType.NONE
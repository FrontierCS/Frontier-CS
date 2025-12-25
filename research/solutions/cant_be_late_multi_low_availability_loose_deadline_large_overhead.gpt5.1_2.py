import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "my_strategy"

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

        # Lazy-init flag for internal state
        self._state_initialized = False
        return self

    def _initialize_state(self):
        if self._state_initialized:
            return

        # Handle possible list types for task_duration and restart_overhead
        td = self.task_duration
        if isinstance(td, (list, tuple)):
            td = td[0]
        ro = self.restart_overhead
        if isinstance(ro, (list, tuple)):
            ro = ro[0]
        dl = self.deadline

        self._task_duration = float(td)
        self._restart_overhead = float(ro)
        self._deadline = float(dl)
        self._dt = float(self.env.gap_seconds)

        # Progress tracking
        self._last_task_segments_len = len(self.task_done_time)
        if self._last_task_segments_len > 0:
            self._total_done = float(sum(self.task_done_time))
        else:
            self._total_done = 0.0

        # Whether we've irrevocably switched to ON_DEMAND
        self._committed_to_on_demand = False

        self._state_initialized = True

    def _update_progress(self):
        cur_len = len(self.task_done_time)
        if cur_len > self._last_task_segments_len:
            # Accumulate only the new segments
            new_segments = self.task_done_time[self._last_task_segments_len:cur_len]
            if new_segments:
                self._total_done += float(sum(new_segments))
            self._last_task_segments_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_state()
        self._update_progress()

        remaining_work = self._task_duration - self._total_done
        if remaining_work <= 0:
            # Task already completed
            return ClusterType.NONE

        # If already committed to on-demand, never go back to spot
        if self._committed_to_on_demand or last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        time_left = self._deadline - self.env.elapsed_seconds
        if time_left <= 0:
            # Past deadline, emergency: use on-demand
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Time needed if we switch to on-demand now (includes one restart overhead)
        safe_time_needed = remaining_work + self._restart_overhead
        slack = time_left - safe_time_needed

        # Safety buffer to guard against discretization and one more restart
        buffer = max(2.0 * self._restart_overhead + self._dt, 2.0 * self._dt)

        # If slack is small, commit to on-demand for the rest of the job
        if slack <= buffer:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Exploration phase: prefer spot when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide between idling and early fallback
        # If we idle one step, new slack will be slack - dt
        if slack - self._dt >= buffer:
            return ClusterType.NONE

        # Not enough slack to idle; switch to on-demand now
        self._committed_to_on_demand = True
        return ClusterType.ON_DEMAND

import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbm_safe_multiregion"

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

        # Internal state for strategy
        self._initialized = False
        self._commit_on_demand = False
        self._no_spot_wait_steps = 0
        return self

    def _init_once(self):
        if self._initialized:
            return
        self._initialized = True
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1
        if self._num_regions is None or self._num_regions <= 0:
            self._num_regions = 1

    def _rotate_region_for_next_step(self):
        if self._num_regions <= 1:
            return
        cur = self.env.get_current_region()
        nxt = (cur + 1) % self._num_regions
        if nxt != cur:
            self.env.switch_region(nxt)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_once()

        # If already committed to on-demand to ensure finish, keep it
        if self._commit_on_demand:
            return ClusterType.ON_DEMAND

        gap = float(self.env.gap_seconds)
        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline - elapsed)

        done = float(sum(self.task_done_time))
        remaining_work = max(0.0, float(self.task_duration - done))

        restart_overhead = float(self.restart_overhead)
        remaining_restart_overhead = float(getattr(self, "remaining_restart_overhead", restart_overhead) or 0.0)

        # Overhead to finish if switching to OD now
        if last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead_now = max(0.0, remaining_restart_overhead)
        else:
            od_overhead_now = restart_overhead

        od_time_needed = od_overhead_now + remaining_work

        # Safety buffers:
        # For running on SPOT this step: ensure we still can fallback to OD next step even if we lose this step (gap)
        # and, if currently on OD, account for paying a fresh restart_overhead when switching back to OD.
        risk_buffer_spot = gap + max(0.0, restart_overhead - od_overhead_now)

        # For waiting (NONE) this step due to no spot: ensure we can still finish by switching to OD next step.
        wait_buffer_none = gap * (1 + max(0, self._no_spot_wait_steps))

        # If time is tight relative to OD finish time, choose OD now to guarantee completion.
        if time_left <= od_time_needed + risk_buffer_spot:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # If SPOT is available and we have enough buffer, run on SPOT
        if has_spot:
            # Reset no-spot waiting counter
            self._no_spot_wait_steps = 0
            return ClusterType.SPOT

        # SPOT not available: decide between waiting (NONE) vs switching to OD
        if time_left <= od_time_needed + wait_buffer_none:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # We have enough slack to wait for SPOT; rotate region to try a different one next step
        self._no_spot_wait_steps += 1
        self._rotate_region_for_next_step()
        return ClusterType.NONE

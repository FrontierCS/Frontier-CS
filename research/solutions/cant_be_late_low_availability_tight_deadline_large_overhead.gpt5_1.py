import argparse
from typing import Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_safe_v2"

    def __init__(self, args: Optional[argparse.Namespace] = None):
        super().__init__(args)
        self._started = False
        self._last_action: ClusterType = ClusterType.NONE
        self._last_has_spot: bool = False
        self._overhead_start_of_last_step: float = 0.0
        self._overhead_end_of_last_step: float = 0.0
        self._internal_progress_done: float = 0.0
        self._committed_to_od: bool = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_progress_from_last_step(self):
        if not self._started:
            return

        dt = float(self.env.gap_seconds)
        if dt <= 0:
            return

        # Whether we were able to do useful work last step
        can_run = False
        if self._last_action == ClusterType.ON_DEMAND:
            can_run = True
        elif self._last_action == ClusterType.SPOT and self._last_has_spot:
            can_run = True
        elif self._last_action == ClusterType.NONE:
            can_run = False

        # Compute contributed work in the last step, accounting for overhead.
        progress_inc = 0.0
        if can_run:
            if self._overhead_start_of_last_step >= dt:
                progress_inc = 0.0
                self._overhead_end_of_last_step = self._overhead_start_of_last_step - dt
            else:
                progress_time = dt - self._overhead_start_of_last_step
                remaining_before = max(0.0, float(self.task_duration) - self._internal_progress_done)
                progress_inc = min(progress_time, remaining_before)
                self._overhead_end_of_last_step = 0.0
        else:
            # No cluster ran; overhead does not tick down because we did not start anything.
            # But overhead start for last step should be zero when last_action is NONE.
            self._overhead_end_of_last_step = self._overhead_start_of_last_step

        self._internal_progress_done = min(
            float(self.task_duration),
            self._internal_progress_done + progress_inc
        )

    def _decide_action(self, has_spot: bool) -> ClusterType:
        # If already committed to OD, just return OD
        if self._committed_to_od:
            return ClusterType.ON_DEMAND

        # Time and remaining work calculations
        now = float(self.env.elapsed_seconds)
        deadline = float(self.deadline)
        dt = float(self.env.gap_seconds)
        time_remaining = max(0.0, deadline - now)

        remaining_compute = max(0.0, float(self.task_duration) - self._internal_progress_done)

        if remaining_compute <= 0.0 or time_remaining <= 0.0:
            return ClusterType.NONE

        # Safety rule: allow wasting one step (dt) and still complete by switching to OD with one restart overhead.
        safety_overhead = float(self.restart_overhead)
        can_spend_one_step = (time_remaining - dt) >= (remaining_compute + safety_overhead)

        if has_spot:
            if can_spend_one_step:
                return ClusterType.SPOT
            else:
                # Commit to OD to guarantee completion
                self._committed_to_od = True
                return ClusterType.ON_DEMAND
        else:
            if can_spend_one_step:
                return ClusterType.NONE
            else:
                # Commit to OD
                self._committed_to_od = True
                return ClusterType.ON_DEMAND

    def _prepare_overhead_for_current_step(self, action: ClusterType):
        # Determine overhead at the start of the current step based on action switching.
        if action == ClusterType.NONE:
            self._overhead_start_of_last_step = 0.0
            return

        if action == self._last_action:
            # Continuing same cluster; carry over any remaining overhead from previous step
            self._overhead_start_of_last_step = max(0.0, self._overhead_end_of_last_step)
        else:
            # Switching clusters; pay restart overhead anew
            self._overhead_start_of_last_step = float(self.restart_overhead)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Update internal progress based on the last step we executed
        self._update_progress_from_last_step()

        # If already finished, do nothing
        if self._internal_progress_done >= float(self.task_duration):
            action = ClusterType.NONE
            # Update tracked state for correctness in subsequent calls
            self._last_action = action
            self._last_has_spot = has_spot
            self._overhead_start_of_last_step = 0.0
            self._overhead_end_of_last_step = 0.0
            self._started = True
            return action

        # Decide action for this step
        action = self._decide_action(has_spot)

        # Prepare overhead for the step we are about to run
        self._prepare_overhead_for_current_step(action)

        # Record state for next step's update
        self._last_action = action
        self._last_has_spot = has_spot
        self._started = True

        return action

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
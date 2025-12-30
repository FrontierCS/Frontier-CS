from typing import Any
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "deadline_hedge_v1"

    def __init__(self, args: Any = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass
        self.args = args
        self._locked_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work_seconds(self) -> float:
        done = 0.0
        try:
            if self.task_done_time:
                for seg in self.task_done_time:
                    done += float(seg)
        except Exception:
            try:
                done = float(self.task_done_time)  # fallback if scalar
            except Exception:
                done = 0.0
        remaining = float(self.task_duration) - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _time_left_seconds(self) -> float:
        left = float(self.deadline) - float(self.env.elapsed_seconds)
        return left if left > 0.0 else 0.0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to on-demand, continue to ensure deadline.
        if self._locked_to_od:
            return ClusterType.ON_DEMAND

        rem = self._remaining_work_seconds()
        if rem <= 0.0:
            return ClusterType.NONE

        time_left = self._time_left_seconds()
        gap = float(self.env.gap_seconds)
        if gap <= 0.0:
            gap = 60.0  # sensible default fallback
        oh = float(self.restart_overhead)

        # Safety buffers to account for discretization and unseen micro-effects.
        buffer_spot = max(1.5 * gap, 1.0)  # when choosing SPOT
        buffer_wait = max(1.2 * gap, 1.0)  # when choosing to wait (NONE)

        # If choosing SPOT now, and last type isn't SPOT, we'll pay overhead for starting SPOT this step,
        # which reduces progress this step by 'oh'. To ensure we can switch to OD next step and still finish,
        # we need enough time: time_left > rem + oh(OD switch later) + oh(if switching to spot now) + buffer.
        oh_spot_now = oh if last_cluster_type != ClusterType.SPOT else 0.0
        safe_to_use_spot_now = time_left > (rem + oh + oh_spot_now + buffer_spot)

        # If choosing to wait (NONE) this step (spot unavailable), to still guarantee finishing by switching
        # to OD next step, we require: time_left - gap >= rem + oh -> time_left > rem + oh + gap (+ buffer).
        safe_to_wait = time_left > (rem + oh + gap + buffer_wait)

        if has_spot:
            if safe_to_use_spot_now:
                return ClusterType.SPOT
            # Not safe to keep using SPOT -> commit to On-Demand now.
            self._locked_to_od = True
            return ClusterType.ON_DEMAND
        else:
            if safe_to_wait:
                return ClusterType.NONE
            # Not safe to wait -> commit to On-Demand now.
            self._locked_to_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
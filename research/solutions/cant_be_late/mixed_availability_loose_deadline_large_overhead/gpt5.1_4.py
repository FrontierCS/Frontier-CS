from collections import deque
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbh_safe_spot_scheduler_v1"

    def __init__(self, args):
        super().__init__(args)
        self._spot_window = deque(maxlen=500)
        self._spot_window_sum = 0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _update_spot_window(self, has_spot: bool):
        val = 1 if has_spot else 0
        if len(self._spot_window) == self._spot_window.maxlen:
            oldest = self._spot_window.popleft()
            self._spot_window_sum -= oldest
        self._spot_window.append(val)
        self._spot_window_sum += val

    def _get_spot_availability(self) -> float:
        if not self._spot_window:
            return 1.0
        return self._spot_window_sum / float(len(self._spot_window))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Track recent spot availability
        self._update_spot_window(has_spot)

        env = self.env
        elapsed = getattr(env, "elapsed_seconds", 0.0)
        gap = getattr(env, "gap_seconds", 1.0)

        deadline = getattr(self, "deadline", float("inf"))
        task_duration = getattr(self, "task_duration", 0.0)
        restart_overhead = getattr(self, "restart_overhead", 0.0)
        done_list = getattr(self, "task_done_time", None)

        # Conservative estimate of completed work
        if done_list:
            done = done_list[-1]
        else:
            done = 0.0

        remaining = task_duration - done
        if remaining <= 0:
            return ClusterType.NONE

        slack = deadline - elapsed
        if slack <= 0:
            # Already at/past deadline: finish as fast as possible
            return ClusterType.ON_DEMAND

        # Safety margin to account for timestep discretization
        margin = max(gap, restart_overhead)

        # Time needed to finish if we switch to on-demand now
        need_time_with_od = remaining + restart_overhead

        # Bail-out condition: ensure we can always finish on time with OD
        if need_time_with_od >= slack - margin:
            return ClusterType.ON_DEMAND

        # Outside bail-out region: exploit spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: decide between waiting and using on-demand
        extra_slack = slack - need_time_with_od
        if extra_slack <= 0:
            # No extra slack beyond minimal requirement
            return ClusterType.ON_DEMAND

        # Base waiting buffer (how much extra slack we require to justify idling)
        wait_buffer = max(3.0 * gap, 1.5 * restart_overhead)

        # Adapt waiting aggressiveness based on recent spot availability
        avail_ratio = self._get_spot_availability()
        if len(self._spot_window) >= 20:
            if avail_ratio >= 0.8:
                # Very reliable spot: more willing to wait
                wait_buffer *= 0.5
            elif avail_ratio <= 0.3:
                # Poor spot availability: switch to OD sooner
                wait_buffer *= 2.0

        if extra_slack > wait_buffer:
            return ClusterType.NONE
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
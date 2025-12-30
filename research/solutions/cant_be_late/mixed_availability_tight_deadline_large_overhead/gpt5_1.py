from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cbldp_threshold_v3"

    def __init__(self, args=None):
        super().__init__(args)
        self._locked_to_od = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _remaining_work(self) -> float:
        done = 0.0
        try:
            if self.task_done_time:
                done = float(sum(self.task_done_time))
        except TypeError:
            total = 0.0
            for seg in self.task_done_time:
                try:
                    total += float(seg)
                except Exception:
                    try:
                        s, e = seg
                        total += float(e) - float(s)
                    except Exception:
                        pass
            done = total
        remaining = self.task_duration - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If already committed to OD or was OD last step, stay OD
        if last_cluster_type == ClusterType.ON_DEMAND:
            self._locked_to_od = True
            return ClusterType.ON_DEMAND
        if self._locked_to_od:
            return ClusterType.ON_DEMAND

        # Gather environment info
        now = float(self.env.elapsed_seconds)
        dt = float(self.env.gap_seconds)
        to_deadline = float(self.deadline) - now
        if to_deadline < 0.0:
            to_deadline = 0.0

        rem = self._remaining_work()
        if rem <= 0.0:
            return ClusterType.NONE

        overhead = float(self.restart_overhead)
        eps = 1e-9

        # If there's no time left, must go OD
        if to_deadline <= 0.0:
            self._locked_to_od = True
            return ClusterType.ON_DEMAND

        slack = to_deadline - rem  # time cushion beyond required compute time

        # If Spot is available
        if has_spot:
            # If currently on SPOT: continue unless slack < overhead and not finishing this step
            if last_cluster_type == ClusterType.SPOT:
                # If we can finish within this step on Spot, just finish
                if rem <= dt + eps:
                    return ClusterType.SPOT
                # Otherwise ensure we maintain enough slack to absorb an OD restart later
                if slack < overhead - eps:
                    self._locked_to_od = True
                    return ClusterType.ON_DEMAND
                return ClusterType.SPOT
            else:
                # Starting SPOT (from NONE). If we can finish this step even after restart overhead, use SPOT.
                effective_compute = max(dt - overhead, 0.0)
                if effective_compute > 0.0 and rem <= effective_compute + eps and to_deadline >= rem + overhead - eps:
                    return ClusterType.SPOT
                # Otherwise, only start SPOT if we can afford to wait one step and still have enough time
                if slack > overhead + dt + eps:
                    return ClusterType.SPOT
                # Too risky to start SPOT now; switch to OD
                self._locked_to_od = True
                return ClusterType.ON_DEMAND

        # Spot not available
        if slack > overhead + dt + eps:
            return ClusterType.NONE

        self._locked_to_od = True
        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
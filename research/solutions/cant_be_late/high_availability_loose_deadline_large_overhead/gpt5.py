import math
from typing import Optional
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "safe_spot_wait_commit_od"

    def __init__(self, args=None):
        self.args = args
        self._committed_to_od: bool = False
        self._od_start_time: Optional[float] = None

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
            # Compute remaining work and time
            done = sum(self.task_done_time) if self.task_done_time else 0.0
            remaining_work = max(0.0, self.task_duration - done)
            if remaining_work <= 0.0:
                # Finished
                return ClusterType.NONE

            elapsed = getattr(self.env, "elapsed_seconds", 0.0) or 0.0
            gap = getattr(self.env, "gap_seconds", 1.0) or 1.0
            deadline = self.deadline
            time_left = max(0.0, deadline - elapsed)

            # Restart overhead and guard margin (seconds)
            overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)
            # Guard margin: one step plus a fraction of overhead to be safe against discretization and overhead application timing
            commit_guard = gap + 0.25 * overhead

            # If we have already committed to on-demand, keep using on-demand to avoid further risks/overheads.
            if self._committed_to_od:
                return ClusterType.ON_DEMAND

            # Determine if we must commit now to guarantee completion even in worst-case future spot unavailability.
            # If (time_left <= remaining_work + overhead + guard), running on-demand from now will finish by deadline.
            # If we delay further, we risk missing due to overhead and discretization.
            if time_left <= remaining_work + overhead + commit_guard:
                self._committed_to_od = True
                self._od_start_time = elapsed
                return ClusterType.ON_DEMAND

            # Not yet in hard commit zone
            if has_spot:
                # Use cheap spot while available, as we're still safely before the commit threshold.
                return ClusterType.SPOT

            # Spot is unavailable: decide whether to wait or switch to on-demand.
            # We can wait at most 'buffer' seconds before starting OD and still finish before deadline.
            buffer = time_left - (remaining_work + overhead)
            if buffer > commit_guard:
                # Still have enough buffer to wait for spot without jeopardizing the deadline.
                return ClusterType.NONE
            else:
                # Buffer is small; switch to OD to guarantee completion.
                self._committed_to_od = True
                self._od_start_time = elapsed
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
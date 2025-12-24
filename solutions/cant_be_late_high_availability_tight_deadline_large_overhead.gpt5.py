import json
import os
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_barrier"

    def __init__(self, args=None):
        super().__init__(args)
        self._committed_od = False
        self._extra_commit_margin_seconds = 0.0

    def solve(self, spec_path: str) -> "Solution":
        try:
            if spec_path and os.path.isfile(spec_path):
                with open(spec_path, "r") as f:
                    cfg = json.load(f)
                self._extra_commit_margin_seconds = float(cfg.get("commit_margin_seconds", 0.0))
        except Exception:
            pass
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        dt = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        oh = float(self.restart_overhead or 0.0)
        deadline = float(self.deadline or 0.0)
        total = float(self.task_duration or 0.0)

        # Compute completed work
        done_list = self.task_done_time
        try:
            if isinstance(done_list, (list, tuple)):
                done = float(sum(done_list))
            else:
                done = float(done_list or 0.0)
        except Exception:
            done = 0.0

        remaining_work = max(0.0, total - done)
        if remaining_work <= 0.0:
            return ClusterType.NONE

        time_left = max(0.0, deadline - elapsed)

        if self._committed_od:
            return ClusterType.ON_DEMAND

        # Slack beyond "finish on OD after one overhead"
        s = time_left - (remaining_work + oh + self._extra_commit_margin_seconds)

        if has_spot:
            if s > 0.0:
                return ClusterType.SPOT
            else:
                self._committed_od = True
                return ClusterType.ON_DEMAND
        else:
            if s >= dt:
                return ClusterType.NONE
            self._committed_od = True
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

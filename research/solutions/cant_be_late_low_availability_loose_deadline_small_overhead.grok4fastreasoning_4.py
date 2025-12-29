from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def solve(self, spec_path: str) -> "Solution":
        self.spot_runs = []
        self.on_spot = False
        self.current_spot_run = 0.0
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        done = sum(self.task_done_time)
        R = self.task_duration - done
        T = self.env.elapsed_seconds
        TL = self.deadline - T
        slack = TL - R
        O = self.restart_overhead
        gap = self.env.gap_seconds

        # Update state based on last_cluster_type
        if last_cluster_type == ClusterType.SPOT:
            self.current_spot_run += gap
            self.on_spot = True
        else:
            if self.on_spot:
                self.spot_runs.append(self.current_spot_run)
                self.current_spot_run = 0.0
                self.on_spot = False

        # Decide
        if not has_spot:
            return ClusterType.ON_DEMAND

        # has_spot is True
        if self.on_spot:
            return ClusterType.SPOT

        # Potential start of new spot run
        if self.spot_runs:
            n_recent = min(5, len(self.spot_runs))
            recent = self.spot_runs[-n_recent:]
            avg = sum(recent) / n_recent
        else:
            avg = 3600.0  # assume 1 hour

        threshold = max(O, gap)
        if avg > threshold and slack > threshold:
            return ClusterType.SPOT
        else:
            return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
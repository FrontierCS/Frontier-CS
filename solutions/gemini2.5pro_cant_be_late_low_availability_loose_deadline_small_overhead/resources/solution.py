import collections

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    WINDOW_SIZE = 100
    BASE_SAFE_THRESHOLD = 0.60
    P_SENSITIVITY = 0.20
    CRITICAL_THRESHOLD = 0.95

    def solve(self, spec_path: str) -> "Solution":
        self.spot_history = collections.deque(maxlen=self.WINDOW_SIZE)
        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.spot_history.append(1 if has_spot else 0)
        if len(self.spot_history) > 0:
            p_hat = sum(self.spot_history) / len(self.spot_history)
        else:
            p_hat = 0.22

        remaining_work = self.remaining_work
        time_to_deadline = self.deadline - self.env.elapsed_seconds

        if remaining_work <= 0:
            return ClusterType.NONE

        if time_to_deadline <= 0:
            return ClusterType.ON_DEMAND

        required_rate = remaining_work / (time_to_deadline + 1e-6)

        dynamic_safe_threshold = self.BASE_SAFE_THRESHOLD + self.P_SENSITIVITY * p_hat

        if required_rate >= self.CRITICAL_THRESHOLD:
            return ClusterType.ON_DEMAND
        elif required_rate < dynamic_safe_threshold:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.NONE
        else:
            if has_spot:
                return ClusterType.SPOT
            else:
                return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

import math
from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType

class Solution(Strategy):
    NAME = "my_solution"

    def __init__(self, args):
        super().__init__(args)
        self.config = {}
        self.last_spot_unavailable_time = None
        self.consecutive_spot_failures = 0
        self.spot_availability_history = []
        self.work_done = 0.0
        self.remaining_work = 0.0
        self.time_elapsed = 0.0
        self.deadline_slack = 0.0

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _estimate_spot_reliability(self) -> float:
        if not self.spot_availability_history:
            return 0.5
        recent_history = self.spot_availability_history[-min(100, len(self.spot_availability_history)):]
        return sum(recent_history) / len(recent_history)

    def _calculate_safe_threshold(self) -> float:
        base_threshold = 0.3
        reliability = self._estimate_spot_reliability()
        reliability_factor = max(0.1, 1.0 - reliability)
        time_pressure = max(0.0, 1.0 - (self.deadline - self.time_elapsed) / self.deadline_slack)
        return base_threshold + 0.4 * time_pressure + 0.2 * reliability_factor

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self.spot_availability_history.append(1 if has_spot else 0)
        if len(self.spot_availability_history) > 1000:
            self.spot_availability_history.pop(0)

        if not has_spot:
            self.consecutive_spot_failures += 1
            self.last_spot_unavailable_time = self.env.elapsed_seconds
        else:
            self.consecutive_spot_failures = 0

        self.time_elapsed = self.env.elapsed_seconds
        if self.task_done_time:
            self.work_done = sum(end - start for start, end in self.task_done_time)
        else:
            self.work_done = 0.0
        self.remaining_work = self.task_duration - self.work_done
        if self.deadline_slack == 0.0:
            self.deadline_slack = self.deadline - self.task_duration

        time_remaining = self.deadline - self.time_elapsed
        
        if self.remaining_work <= 0:
            return ClusterType.NONE

        if time_remaining <= 0:
            return ClusterType.ON_DEMAND

        required_rate = self.remaining_work / time_remaining
        max_spot_rate = 1.0 if has_spot else 0.0

        if required_rate > 0.95:
            return ClusterType.ON_DEMAND

        if time_remaining - self.remaining_work < self.restart_overhead * 2:
            return ClusterType.ON_DEMAND

        safe_threshold = self._calculate_safe_threshold()

        if has_spot:
            if required_rate < safe_threshold:
                return ClusterType.SPOT
            else:
                if self.consecutive_spot_failures > 5:
                    return ClusterType.ON_DEMAND
                time_since_last_failure = 0
                if self.last_spot_unavailable_time is not None:
                    time_since_last_failure = self.time_elapsed - self.last_spot_unavailable_time
                if time_since_last_failure > self.restart_overhead * 10:
                    return ClusterType.SPOT
                else:
                    if required_rate > 0.5:
                        return ClusterType.ON_DEMAND
                    else:
                        return ClusterType.SPOT if time_since_last_failure > self.restart_overhead else ClusterType.NONE
        else:
            if required_rate > 0.7:
                return ClusterType.ON_DEMAND
            elif required_rate > 0.3:
                if self.consecutive_spot_failures < 3:
                    return ClusterType.NONE
                else:
                    return ClusterType.ON_DEMAND
            else:
                return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

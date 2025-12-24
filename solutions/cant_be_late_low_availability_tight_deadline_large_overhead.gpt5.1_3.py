from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_heuristic_v1"

    def __init__(self, args):
        super().__init__(args)
        self.args = args
        self._committed_to_on_demand = False
        self._slack_total = None
        self._commit_threshold = None
        self._slack_idle_threshold = None
        self._params_initialized = False

    def solve(self, spec_path: str) -> "Solution":
        return self

    def _initialize_params_if_needed(self):
        if self._params_initialized:
            return

        try:
            slack_total = max(self.deadline - self.task_duration, 0.0)
        except Exception:
            slack_total = 0.0
        self._slack_total = slack_total

        restart_overhead = getattr(self, "restart_overhead", 0.0) or 0.0

        if slack_total <= 0.0:
            commit_threshold = 0.0
            idle_threshold = 0.0
        else:
            commit_threshold = max(2.0 * restart_overhead, 0.15 * slack_total)
            commit_threshold = min(commit_threshold, 0.5 * slack_total)

            idle_threshold = max(commit_threshold + 0.25 * slack_total,
                                 0.6 * slack_total)
            idle_threshold = min(idle_threshold, 0.9 * slack_total)

        self._commit_threshold = commit_threshold
        self._slack_idle_threshold = idle_threshold
        self._params_initialized = True

    def _compute_remaining_work(self) -> float:
        done = 0.0
        task_done_time = getattr(self, "task_done_time", None)
        if task_done_time:
            try:
                done = float(sum(task_done_time))
            except TypeError:
                done = 0.0
                for seg in task_done_time:
                    try:
                        done += float(seg)
                    except Exception:
                        continue
        remaining = self.task_duration - done
        if remaining < 0.0:
            remaining = 0.0
        return remaining

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_params_if_needed()

        remaining_work = self._compute_remaining_work()
        if remaining_work <= 0.0:
            self._committed_to_on_demand = False
            return ClusterType.NONE

        time_left = self.deadline - self.env.elapsed_seconds
        if time_left <= 0.0:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        slack_left = time_left - remaining_work

        if slack_left <= 0.0:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        if (not self._committed_to_on_demand and
                slack_left <= self._commit_threshold):
            self._committed_to_on_demand = True

        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if slack_left > self._slack_idle_threshold:
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

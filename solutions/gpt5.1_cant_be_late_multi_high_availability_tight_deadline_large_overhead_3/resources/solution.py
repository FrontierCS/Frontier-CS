import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy."""

    NAME = "cant_be_late_mr_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal state
        self._committed_to_on_demand = False
        self._commit_threshold_seconds = None
        return self

    @staticmethod
    def _get_scalar(value):
        """Return a scalar float from possibly list/tuple or scalar."""
        if isinstance(value, (list, tuple)):
            if not value:
                return 0.0
            try:
                return float(value[0])
            except Exception:
                try:
                    return float(value)
                except Exception:
                    return 0.0
        try:
            return float(value)
        except Exception:
            return 0.0

    def _ensure_commit_threshold(self) -> float:
        """Initialize and return the commit threshold in seconds."""
        if self._commit_threshold_seconds is None:
            gap = getattr(self.env, "gap_seconds", 1.0)
            restart_overhead = self._get_scalar(getattr(self, "restart_overhead", 0.0))
            # Safety threshold: large enough to cover worst-case one-step loss
            # (gap + restart_overhead), plus extra margin.
            self._commit_threshold_seconds = 2.0 * (gap + restart_overhead)
        return self._commit_threshold_seconds

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Keep internal flag consistent if we are already on on-demand
        if not self._committed_to_on_demand and last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_to_on_demand = True

        env = self.env
        gap = getattr(env, "gap_seconds", 1.0)
        elapsed = getattr(env, "elapsed_seconds", 0.0)

        # Compute work done so far
        done_segments = getattr(self, "task_done_time", None)
        if done_segments:
            try:
                work_done = float(sum(done_segments))
            except Exception:
                work_done = 0.0
        else:
            work_done = 0.0

        total_duration = self._get_scalar(getattr(self, "task_duration", 0.0))
        remaining_work = max(total_duration - work_done, 0.0)

        # If task is complete, no need to run more
        if remaining_work <= 0.0:
            return ClusterType.NONE

        deadline = self._get_scalar(getattr(self, "deadline", 0.0))
        time_left = deadline - elapsed

        # If already past deadline, stop incurring cost
        if time_left <= 0.0:
            return ClusterType.NONE

        # If we've already committed, always use on-demand
        if self._committed_to_on_demand:
            return ClusterType.ON_DEMAND

        restart_overhead = self._get_scalar(getattr(self, "restart_overhead", 0.0))
        commit_threshold = self._ensure_commit_threshold()

        # Time required to safely finish if we switch to on-demand now
        required_time = remaining_work + restart_overhead
        slack = time_left - required_time

        # Commit to on-demand when slack becomes small
        if slack <= commit_threshold:
            self._committed_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Before commit: prefer spot if available
        if has_spot:
            return ClusterType.SPOT

        # Spot not available: decide whether to wait (NONE) or go early to on-demand
        time_left_after_wait = time_left - gap
        slack_after_wait = time_left_after_wait - required_time

        if slack_after_wait > commit_threshold:
            # Still safe to wait; also try another region for future spots
            try:
                num_regions = env.get_num_regions()
            except Exception:
                num_regions = 1
            if num_regions and num_regions > 1:
                try:
                    current_region = env.get_current_region()
                    next_region = (current_region + 1) % num_regions
                    env.switch_region(next_region)
                except Exception:
                    # If any of the region utilities fail, just ignore and stay put
                    pass
            return ClusterType.NONE

        # Slack is tight; switch to on-demand now to avoid missing deadline
        self._committed_to_on_demand = True
        return ClusterType.ON_DEMAND

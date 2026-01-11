import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with deadline-aware spot usage."""

    NAME = "my_strategy"

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

        # Custom state initialization
        self._initialized = False
        self._total_progress = 0.0
        self._last_total_progress = 0.0
        self._task_done_len = 0
        self._last_elapsed = 0.0
        self._last_region = 0
        self._force_on_demand = False

        self._num_regions = None
        self._gap_seconds = None

        self._task_duration = None
        self._deadline = None
        self._restart_overhead = None
        self._total_slack = None
        self._safety_margin = None
        self._large_slack_threshold = None

        return self

    def _initialize_if_needed(self):
        if self._initialized:
            return

        self._initialized = True

        # Extract scalar versions of core parameters (in seconds)
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration = float(sum(td))
        elif td is not None:
            self._task_duration = float(td)
        else:
            self._task_duration = 0.0

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            self._deadline = float(dl[0])
        elif dl is not None:
            self._deadline = float(dl)
        else:
            self._deadline = 0.0

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        elif ro is not None:
            self._restart_overhead = float(ro)
        else:
            self._restart_overhead = 0.0

        # Initial cumulative progress from any pre-run state
        self._task_done_len = len(self.task_done_time)
        if self._task_done_len > 0:
            self._total_progress = sum(self.task_done_time)
        else:
            self._total_progress = 0.0
        self._last_total_progress = self._total_progress

        self._last_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))

        try:
            self._last_region = self.env.get_current_region()
        except Exception:
            self._last_region = 0

        try:
            self._gap_seconds = float(self.env.gap_seconds)
        except Exception:
            self._gap_seconds = 1.0

        # Overall slack (seconds)
        self._total_slack = max(self._deadline - self._task_duration, 0.0)

        # Safety margin before deadline to commit to ON_DEMAND.
        # Use a conservative function of restart_overhead and total slack.
        r = self._restart_overhead
        # Margin is at most 1 hour, and at most 10% of slack, and at least 0.
        self._safety_margin = min(
            max(0.0, 2.0 * r),
            max(0.0, 0.1 * self._total_slack),
            3600.0,
        )

        # Threshold of slack (beyond required ON_DEMAND time) above which we are
        # comfortable idling (NONE) when spot is unavailable.
        # At most 2 hours or 25% of slack.
        self._large_slack_threshold = min(7200.0, 0.25 * self._total_slack)
        if self._large_slack_threshold < 0.0:
            self._large_slack_threshold = 0.0

        try:
            self._num_regions = self.env.get_num_regions()
        except Exception:
            self._num_regions = 1

    def _update_progress_and_stats(self, last_cluster_type: ClusterType):
        # Incrementally update cumulative progress based on new segments
        if len(self.task_done_time) > self._task_done_len:
            for i in range(self._task_done_len, len(self.task_done_time)):
                self._total_progress += self.task_done_time[i]
            self._task_done_len = len(self.task_done_time)

        current_elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        dt = current_elapsed - self._last_elapsed
        if dt < 0.0:
            dt = 0.0

        _ = dt  # placeholder for potential future stats
        dprogress = self._total_progress - self._last_total_progress
        _ = dprogress  # placeholder for potential future stats

        self._last_elapsed = current_elapsed
        try:
            self._last_region = self.env.get_current_region()
        except Exception:
            pass
        self._last_total_progress = self._total_progress

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Lazy initialization when environment is ready
        self._initialize_if_needed()

        # Update observed progress based on last step's outcome
        self._update_progress_and_stats(last_cluster_type)

        # Remaining work to finish (seconds)
        remaining_work = self._task_duration - self._total_progress
        if remaining_work <= 0.0:
            # Job finished: avoid any further cost
            return ClusterType.NONE

        # Time left until deadline (seconds)
        current_time = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = self._deadline - current_time

        # If past deadline, nothing better than trying to run on ON_DEMAND
        if time_left <= 0.0:
            return ClusterType.ON_DEMAND

        # Estimate future overhead if we switch/continue to ON_DEMAND only from now
        try:
            remaining_overhead_now = float(self.remaining_restart_overhead)
        except Exception:
            remaining_overhead_now = 0.0

        if last_cluster_type == ClusterType.ON_DEMAND:
            od_overhead_future = max(remaining_overhead_now, 0.0)
        else:
            od_overhead_future = self._restart_overhead

        required_time_od_only = remaining_work + od_overhead_future

        # Decide if we must irrevocably commit to ON_DEMAND to safely meet deadline
        if self._force_on_demand or time_left <= required_time_od_only + self._safety_margin:
            self._force_on_demand = True
            return ClusterType.ON_DEMAND

        # Flexible phase: prefer SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable: choose between waiting (NONE) and partial ON_DEMAND usage
        slack_after_od = time_left - required_time_od_only

        # If we still have comfortable slack after accounting for ON_DEMAND time,
        # it is safe and cheaper to wait.
        if slack_after_od > self._large_slack_threshold:
            return ClusterType.NONE

        # Slack is starting to tighten but we are not yet forced to commit;
        # use ON_DEMAND here to make progress.
        return ClusterType.ON_DEMAND
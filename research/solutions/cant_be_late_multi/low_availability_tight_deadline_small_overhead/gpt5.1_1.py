import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy focusing on deadline safety and low cost."""

    NAME = "cant_be_late_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        deadline_hours = float(config["deadline"])
        duration_hours = float(config["duration"])
        overhead_hours = float(config["overhead"])

        args = Namespace(
            deadline_hours=deadline_hours,
            task_duration_hours=[duration_hours],
            restart_overhead_hours=[overhead_hours],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Cache scalar parameters (in seconds, as provided by the environment).
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            td = td[0]
        self._task_duration = float(td)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            dl = dl[0]
        self._deadline = float(dl)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            ro = ro[0]
        self._restart_overhead = float(ro)

        # Progress tracking.
        self._cached_progress = 0.0
        self._last_task_done_len = 0

        # Whether we've committed to always using on-demand.
        self._force_on_demand = False

        # Safe slack margin before we must commit to on-demand (seconds).
        self._safe_margin = None

        return self

    def _initialize_if_needed(self):
        """Lazy initialization in case the strategy is constructed without solve()."""
        if hasattr(self, "_cached_progress"):
            return

        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            td = td[0]
        self._task_duration = float(td)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            dl = dl[0]
        self._deadline = float(dl)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            ro = ro[0]
        self._restart_overhead = float(ro)

        self._cached_progress = 0.0
        self._last_task_done_len = 0
        self._force_on_demand = False
        self._safe_margin = None

    def _update_progress_cache(self):
        """Incrementally track total completed work from task_done_time."""
        task_done = getattr(self, "task_done_time", [])
        current_len = len(task_done)

        # Handle potential reset between runs (defensive).
        if current_len < self._last_task_done_len:
            self._cached_progress = 0.0
            self._last_task_done_len = 0
            current_len = len(task_done)

        if current_len > self._last_task_done_len:
            total_new = 0.0
            for i in range(self._last_task_done_len, current_len):
                total_new += task_done[i]
            self._cached_progress += total_new
            self._last_task_done_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._initialize_if_needed()
        self._update_progress_cache()

        # Remaining work in seconds.
        remaining_work = self._task_duration - self._cached_progress
        if remaining_work <= 0.0:
            # Job already done; no need to run anything.
            return ClusterType.NONE

        # Initialize safe margin once we know gap_seconds.
        if self._safe_margin is None:
            gap = float(self.env.gap_seconds)
            # Safety factor slightly above theoretical minimum to hedge against
            # modeling uncertainties, but still tiny relative to total slack.
            safety_factor = 1.5
            self._safe_margin = safety_factor * (gap + self._restart_overhead)

        # Compute slack if we were to switch to pure on-demand *now*.
        # Conservative: assume we pay one full restart_overhead when we commit.
        elapsed = float(self.env.elapsed_seconds)
        slack_for_on_demand = self._deadline - (
            elapsed + self._restart_overhead + remaining_work
        )

        # Decide whether to commit to on-demand forever.
        if (not self._force_on_demand) and (slack_for_on_demand <= self._safe_margin):
            self._force_on_demand = True

        if self._force_on_demand:
            # From now on, always use on-demand to deterministically finish by deadline.
            return ClusterType.ON_DEMAND

        # Pre-commit phase: use Spot when available, otherwise idle to preserve
        # remaining work for future cheap Spot, while we still have enough slack
        # to fall back to on-demand later.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE
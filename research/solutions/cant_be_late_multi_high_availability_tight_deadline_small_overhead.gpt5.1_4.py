import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Your multi-region scheduling strategy."""

    NAME = "my_strategy"  # REQUIRED: unique identifier

    def solve(self, spec_path: str) -> "Solution":
        """
        Initialize the solution from spec_path config.
        """
        with open(spec_path) as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Cache scalar versions of core parameters for internal use
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration_total = float(td[0])
        else:
            self._task_duration_total = float(td)

        dl = getattr(self, "deadline", None)
        if isinstance(dl, (list, tuple)):
            self._deadline_total = float(dl[0])
        else:
            self._deadline_total = float(dl)

        ro = getattr(self, "restart_overhead", None)
        if isinstance(ro, (list, tuple)):
            self._restart_overhead = float(ro[0])
        else:
            self._restart_overhead = float(ro)

        # Internal episode state
        self._prev_elapsed = None
        self._locked_to_on_demand = False
        self._dt_max = None
        self._spot_safety_offset = None
        self._task_done_accum = 0.0
        self._last_task_done_len = 0

        return self

    def _reset_episode_state(self) -> None:
        """Reset internal state at the start of each new episode."""
        self._locked_to_on_demand = False
        self._task_done_accum = 0.0
        self._last_task_done_len = 0

        gap = getattr(self.env, "gap_seconds", 0.0) or 0.0
        restart = self._restart_overhead
        # Maximum wall-clock increase during one risky (non-OD-locked) step:
        # baseline step + at most one restart_overhead.
        self._dt_max = gap + restart
        # Additional time we must reserve before deadline when taking a risky step:
        # dt_max (time we may waste before we can react) + one restart_overhead
        # for when we finally commit to ON_DEMAND.
        self._spot_safety_offset = self._dt_max + restart

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.
        """
        t = self.env.elapsed_seconds

        # Detect new episode by elapsed_seconds reset
        if self._prev_elapsed is None or t < self._prev_elapsed:
            self._reset_episode_state()
        self._prev_elapsed = t

        # Incremental computation of total work done to avoid O(N^2) summations
        segments = getattr(self, "task_done_time", [])
        n = len(segments)
        if n > self._last_task_done_len:
            # Sum only the newly added segments
            self._task_done_accum += sum(segments[self._last_task_done_len:n])
            self._last_task_done_len = n
        elif n < self._last_task_done_len:
            # In case of unexpected shrink, recompute from scratch
            self._task_done_accum = sum(segments)
            self._last_task_done_len = n

        work_done = self._task_done_accum
        rem_work = self._task_duration_total - work_done

        # If task is (numerically) complete, don't run more compute
        if rem_work <= 0.0:
            return ClusterType.NONE

        time_left = self._deadline_total - t

        # Decide whether to lock into ON_DEMAND to guarantee meeting deadline
        if not self._locked_to_on_demand:
            # Safe to continue using SPOT (or idling) for another step only if:
            #   t + dt_max + restart_overhead + rem_work <= deadline
            # => time_left >= rem_work + spot_safety_offset
            if time_left < rem_work + self._spot_safety_offset:
                self._locked_to_on_demand = True

        if self._locked_to_on_demand:
            # From now until completion, always use ON_DEMAND to avoid further risk.
            return ClusterType.ON_DEMAND

        # Still in SPOT-preferred phase: use SPOT when available, otherwise pause.
        if has_spot:
            return ClusterType.SPOT
        else:
            return ClusterType.NONE

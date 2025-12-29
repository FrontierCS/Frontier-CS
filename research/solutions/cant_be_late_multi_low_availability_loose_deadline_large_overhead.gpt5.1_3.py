import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy aiming for low cost without missing deadline."""

    NAME = "cant_be_late_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        duration_hours = float(config["duration"])
        overhead_hours = float(config["overhead"])
        deadline_hours = float(config["deadline"])

        args = Namespace(
            deadline_hours=deadline_hours,
            task_duration_hours=[duration_hours],
            restart_overhead_hours=[overhead_hours],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        # Internal continuous-time parameters (seconds)
        self._task_duration_seconds = duration_hours * 3600.0
        self._deadline_seconds = deadline_hours * 3600.0
        self._restart_overhead_seconds = overhead_hours * 3600.0

        # Progress tracking
        self._progress_seconds = 0.0
        self._last_task_done_len = 0

        # Fallback control
        self._commit_to_on_demand = False

        # Region statistics, initialized lazily once env is attached
        self._env_initialized = False

        return self

    def _lazy_env_init(self):
        if self._env_initialized:
            return
        num_regions = self.env.get_num_regions()
        self._num_regions = num_regions
        self._region_visits = [0] * num_regions
        self._region_spot_true = [0] * num_regions
        # Beta(1,1) prior for availability probability
        self._alpha = 1.0
        self._beta = 1.0
        self._env_initialized = True

    def _update_progress(self):
        """Incrementally track total work done in seconds."""
        td = self.task_done_time
        cur_len = len(td)
        if cur_len > self._last_task_done_len:
            added = 0.0
            for i in range(self._last_task_done_len, cur_len):
                added += td[i]
            self._progress_seconds += added
            self._last_task_done_len = cur_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure env-dependent state initialized
        self._lazy_env_init()

        # Update cumulative progress
        self._update_progress()

        # If task already completed, do nothing
        if self._progress_seconds >= self._task_duration_seconds - 1e-6:
            return ClusterType.NONE

        # Update region statistics using current has_spot observation
        current_region = self.env.get_current_region()
        if 0 <= current_region < self._num_regions:
            self._region_visits[current_region] += 1
            if has_spot:
                self._region_spot_true[current_region] += 1

        # Compute remaining work and time
        remaining_work = self._task_duration_seconds - self._progress_seconds
        if remaining_work < 0.0:
            remaining_work = 0.0

        time_left = self._deadline_seconds - self.env.elapsed_seconds

        # If somehow past deadline, immediately switch to On-Demand
        if time_left <= 0.0:
            self._commit_to_on_demand = True
        else:
            # Decide whether we must commit to On-Demand to avoid being late.
            # We require that if we wait one more step (worst case, no progress),
            # we can still finish the job entirely on On-Demand.
            if not self._commit_to_on_demand:
                gap = getattr(self.env, "gap_seconds", 0.0)
                # Safe to delay one more step iff:
                # time_left >= remaining_work + restart_overhead + gap
                threshold = remaining_work + self._restart_overhead_seconds + gap
                if time_left < threshold:
                    self._commit_to_on_demand = True

        # Once committed, stay on On-Demand until completion
        if self._commit_to_on_demand:
            return ClusterType.ON_DEMAND

        # Pre-commit phase: prefer Spot when available, otherwise idle
        if has_spot:
            action = ClusterType.SPOT
        else:
            action = ClusterType.NONE

        # Region selection: only switch regions on idle steps (NONE) to avoid
        # interfering with running work and minimize potential restart overhead.
        if (not has_spot) and self._num_regions > 1:
            alpha = self._alpha
            beta = self._beta

            # Current region score
            v_cur = self._region_visits[current_region]
            s_cur = self._region_spot_true[current_region]
            cur_score = (s_cur + alpha) / (v_cur + alpha + beta)

            best_region = current_region
            best_score = cur_score

            # Find region with highest estimated availability
            for i in range(self._num_regions):
                if i == current_region:
                    continue
                v = self._region_visits[i]
                s = self._region_spot_true[i]
                score = (s + alpha) / (v + alpha + beta)
                if score > best_score + 1e-9:
                    best_score = score
                    best_region = i

            # Switch if another region looks strictly better
            if best_region != current_region:
                self.env.switch_region(best_region)

        # Ensure we never request Spot when it's unavailable
        if action == ClusterType.SPOT and not has_spot:
            # Fallback safety: should not normally happen
            action = ClusterType.NONE

        return action
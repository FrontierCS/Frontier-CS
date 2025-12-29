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

        The spec file contains:
        - deadline: deadline in hours
        - duration: task duration in hours
        - overhead: restart overhead in hours
        - trace_files: list of trace file paths (one per region)
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

        # Internal initialization flag; actual init happens on first _step
        self._mr_initialized = False
        return self

    def _ensure_initialized(self):
        """Lazy initialization that depends on the environment being ready."""
        if getattr(self, "_mr_initialized", False):
            return
        self._mr_initialized = True

        # Extract scalar task duration
        td_attr = getattr(self, "task_duration", None)
        if isinstance(td_attr, (list, tuple)):
            self._task_duration = float(td_attr[0])
        else:
            self._task_duration = float(td_attr if td_attr is not None else 0.0)

        # Extract scalar deadline
        dl_attr = getattr(self, "deadline", None)
        if isinstance(dl_attr, (list, tuple)):
            self._deadline = float(dl_attr[0])
        else:
            self._deadline = float(dl_attr if dl_attr is not None else 0.0)

        # Extract scalar restart overhead
        ro_attr = getattr(self, "restart_overhead", None)
        if isinstance(ro_attr, (list, tuple)):
            self._restart_overhead = float(ro_attr[0])
        else:
            self._restart_overhead = float(ro_attr if ro_attr is not None else 0.0)

        # Gap between time steps
        gap = getattr(self.env, "gap_seconds", None)
        self._gap_seconds = float(gap) if gap is not None else 60.0

        # Region-related state
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = 1
        if num_regions <= 0:
            num_regions = 1
        self._num_regions = num_regions
        self._region_total_obs = [0] * num_regions
        self._region_spot_up = [0] * num_regions
        self._region_no_spot_streak = [0] * num_regions

        # Track task progress efficiently
        try:
            initial_done_list = list(self.task_done_time)
        except Exception:
            initial_done_list = []
        if initial_done_list:
            self._done_time_sum = float(sum(initial_done_list))
            self._last_task_done_len = len(initial_done_list)
        else:
            self._done_time_sum = 0.0
            self._last_task_done_len = 0

        # Once we "commit" to on-demand, we stay on it
        self._commit_to_on_demand = False

        # Parameters controlling behavior
        # After this many consecutive no-spot steps in a region, we consider switching.
        self._switch_threshold = 3
        # Margin multiplier when computing safe commit time to on-demand
        self._commit_margin_factor = 4.0

    def _update_task_done_sum(self):
        """Update cached sum(self.task_done_time) in O(Δn) per step."""
        current_list = self.task_done_time
        try:
            current_len = len(current_list)
        except Exception:
            current_len = 0
        if current_len > self._last_task_done_len:
            inc_sum = 0.0
            for v in current_list[self._last_task_done_len:]:
                inc_sum += float(v)
            self._done_time_sum += inc_sum
            self._last_task_done_len = current_len

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        self._ensure_initialized()

        # Efficiently track how much work is done
        self._update_task_done_sum()
        remaining_work = self._task_duration - self._done_time_sum
        if remaining_work <= 0.0:
            # Task is finished; no need to run more clusters.
            self._commit_to_on_demand = True
            return ClusterType.NONE

        # Determine current region and ensure region arrays are sized appropriately
        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0
        if cur_region < 0:
            cur_region = 0
        if cur_region >= self._num_regions:
            # Environment may expose more regions than initially; resize if needed.
            try:
                new_num = int(self.env.get_num_regions())
            except Exception:
                new_num = self._num_regions
            if new_num <= 0:
                new_num = self._num_regions
            if new_num > self._num_regions:
                add = new_num - self._num_regions
                self._region_total_obs.extend([0] * add)
                self._region_spot_up.extend([0] * add)
                self._region_no_spot_streak.extend([0] * add)
                self._num_regions = new_num
            cur_region = min(cur_region, self._num_regions - 1)

        # Update per-region statistics with this step's observation
        self._region_total_obs[cur_region] += 1
        if has_spot:
            self._region_spot_up[cur_region] += 1
            self._region_no_spot_streak[cur_region] = 0
        else:
            self._region_no_spot_streak[cur_region] += 1

        # Remaining wall-clock time until deadline
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        remaining_time = self._deadline - elapsed

        # If already at/past deadline, just run on-demand to minimize further lateness.
        if remaining_time <= 0.0:
            self._commit_to_on_demand = True
            return ClusterType.ON_DEMAND

        # Compute conservative time needed to finish if we move to on-demand now.
        needed_time = remaining_work + self._restart_overhead
        # Add margin for discretization and model mismatch.
        margin = self._commit_margin_factor * max(self._restart_overhead, self._gap_seconds)

        if (not self._commit_to_on_demand) and remaining_time <= needed_time + margin:
            self._commit_to_on_demand = True

        if self._commit_to_on_demand:
            # Once we commit, always use on-demand to guarantee completion.
            return ClusterType.ON_DEMAND

        # Not committed yet: prefer Spot whenever available.
        if has_spot:
            return ClusterType.SPOT

        # Spot unavailable in current region and we're still far from deadline.
        # Optionally switch regions if this one has had a long no-spot streak.
        if self._num_regions > 1:
            streak = self._region_no_spot_streak[cur_region]
            if streak >= self._switch_threshold:
                best_region = cur_region
                best_score = -1.0
                for i in range(self._num_regions):
                    if i == cur_region:
                        continue
                    tot = self._region_total_obs[i]
                    up = self._region_spot_up[i]
                    if tot <= 0:
                        # Mild optimism for unexplored regions to encourage exploration.
                        score = 0.6
                    else:
                        score = up / tot
                    if score > best_score + 1e-9:
                        best_score = score
                        best_region = i
                if best_region != cur_region:
                    # Reset streak for old region before switching to avoid oscillations.
                    self._region_no_spot_streak[cur_region] = 0
                    try:
                        self.env.switch_region(best_region)
                    except Exception:
                        # If switching fails for any reason, just stay in current region.
                        pass

        # No spot currently; wait without incurring cost.
        return ClusterType.NONE
import os
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

        # Store config and trace files for potential use.
        self._spec_config = config
        self._trace_files = config.get("trace_files") or []

        # Determine NONE cluster type if available.
        try:
            self._none_cluster_type = ClusterType.NONE
        except AttributeError:
            self._none_cluster_type = getattr(ClusterType, "None", None)

        self._can_idle = self._none_cluster_type is not None

        # Pre-analyze traces to pick a preferred region (highest average availability).
        self._preferred_region = None
        if self._trace_files:
            base_dir = os.path.dirname(spec_path)
            best_avail = -1.0
            for idx, rel_path in enumerate(self._trace_files):
                full_path = rel_path
                if not os.path.isabs(full_path):
                    full_path = os.path.join(base_dir, rel_path)
                try:
                    with open(full_path, "r") as tf:
                        txt = tf.read().strip()
                except Exception:
                    continue
                if not txt:
                    continue

                arr = None
                # Try JSON first.
                try:
                    data = json.loads(txt)
                    if isinstance(data, list):
                        arr = data
                    elif isinstance(data, dict):
                        for key in ("availability", "values", "data", "spot"):
                            v = data.get(key)
                            if isinstance(v, list):
                                arr = v
                                break
                except Exception:
                    arr = None

                # Fallback: whitespace / comma separated tokens.
                if arr is None:
                    tokens = txt.replace(",", " ").split()
                    arr = []
                    for tok in tokens:
                        t = tok.strip()
                        if not t:
                            continue
                        l = t.lower()
                        if l in ("1", "true", "t", "spot", "available", "avail", "yes", "y"):
                            arr.append(1)
                        elif l in ("0", "false", "f", "none", "unavailable", "na", "no", "n"):
                            arr.append(0)
                        else:
                            try:
                                v = float(t)
                                arr.append(1 if v > 0 else 0)
                            except Exception:
                                pass

                total = 0.0
                count = 0
                for v in arr:
                    if isinstance(v, (list, tuple)):
                        if not v:
                            continue
                        vv = v[1] if len(v) > 1 else v[0]
                    else:
                        vv = v
                    try:
                        val = float(vv)
                    except Exception:
                        continue
                    total += 1.0 if val > 0 else 0.0
                    count += 1
                if count == 0:
                    continue
                avail = total / count
                if avail > best_avail:
                    best_avail = avail
                    self._preferred_region = idx

        # Runtime state initialization.
        self._initialized_runtime = False
        # If we cannot idle, fall back to always using on-demand.
        self._force_on_demand = not self._can_idle
        self._total_done = 0.0
        self._last_task_len = 0
        self._target_region = None
        self._home_region = None
        self._gap_seconds = None

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        """
        Decide next action based on current state.

        Available attributes:
        - self.env.get_current_region(): Get current region index
        - self.env.get_num_regions(): Get total number of regions
        - self.env.switch_region(idx): Switch to region by index
        - self.env.elapsed_seconds: Current time elapsed
        - self.task_duration: Total task duration needed (seconds)
        - self.deadline: Deadline time (seconds)
        - self.restart_overhead: Restart overhead (seconds)
        - self.task_done_time: List of completed work segments
        - self.remaining_restart_overhead: Current pending overhead

        Returns: ClusterType.SPOT, ClusterType.ON_DEMAND, or ClusterType.NONE
        """
        env = self.env

        # One-time runtime initialization.
        if not self._initialized_runtime:
            self._initialized_runtime = True
            try:
                gap = float(getattr(env, "gap_seconds", 0.0))
                if gap <= 0:
                    gap = 60.0
            except Exception:
                gap = 60.0
            self._gap_seconds = gap
            try:
                self._home_region = env.get_current_region()
            except Exception:
                self._home_region = 0
            self._target_region = self._preferred_region if self._preferred_region is not None else self._home_region

        # Maintain current region if we haven't committed to on-demand yet.
        if not self._force_on_demand and self._target_region is not None:
            try:
                cur_region = env.get_current_region()
            except Exception:
                cur_region = None
            if cur_region is not None and cur_region != self._target_region:
                env.switch_region(self._target_region)

        # Efficiently track total completed work.
        tdt = self.task_done_time
        cur_len = len(tdt)
        if cur_len > self._last_task_len:
            incr = 0.0
            for i in range(self._last_task_len, cur_len):
                incr += float(tdt[i])
            self._total_done += incr
            self._last_task_len = cur_len

        remaining_work = self.task_duration - self._total_done

        # If task is already complete, idle if possible.
        if remaining_work <= 0:
            if self._can_idle:
                return self._none_cluster_type
            else:
                return ClusterType.ON_DEMAND

        elapsed = getattr(env, "elapsed_seconds", 0.0)
        deadline = self.deadline
        restart = self.restart_overhead

        # Decide whether we must commit to on-demand to safely meet the deadline.
        if not self._force_on_demand:
            # Slack if we commit to ON_DEMAND now and run uninterrupted.
            slack_now = deadline - elapsed - restart - remaining_work
            gap = self._gap_seconds

            # Only safe to gamble for at least one more step if slack_now >= gap.
            if slack_now <= gap or slack_now < 0:
                self._force_on_demand = True

        # If committed, always use on-demand until completion.
        if self._force_on_demand:
            return ClusterType.ON_DEMAND

        # Before commit: use Spot when available, otherwise idle (if possible).
        if has_spot:
            return ClusterType.SPOT
        else:
            if self._can_idle:
                return self._none_cluster_type
            else:
                # Fallback if NONE is unavailable: commit to on-demand.
                self._force_on_demand = True
                return ClusterType.ON_DEMAND

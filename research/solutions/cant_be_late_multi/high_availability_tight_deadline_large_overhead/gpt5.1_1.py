import json
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    """Multi-region scheduling strategy with hard-deadline guarantee."""
    NAME = "cant_be_late_multi_region_heuristic"

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

        # Caches and state
        self._od_committed = False
        self._work_done_cache = 0.0
        self._last_num_segments = 0
        self._region_initialized = False

        # Task duration in seconds (handle both scalar and list forms)
        td = getattr(self, "task_duration", None)
        if isinstance(td, (list, tuple)):
            self._task_duration_sec = float(td[0])
        elif td is not None:
            self._task_duration_sec = float(td)
        else:
            # Fallback if parent class changes interface
            self._task_duration_sec = float(config["duration"]) * 3600.0

        # Choose a preferred region based on trace availability (best-effort, safe fallback)
        trace_files = config.get("trace_files")
        self._preferred_region = 0
        if isinstance(trace_files, list) and trace_files:
            self._preferred_region = self._infer_best_region(trace_files)

        return self

    def _infer_best_region(self, trace_files):
        """Heuristically select region with highest spot availability from traces."""
        best_idx = 0
        best_ratio = -1.0

        for idx, path in enumerate(trace_files):
            avail = 0
            total = 0
            try:
                with open(path, "r") as f:
                    for line in f:
                        if total >= 10000:
                            break  # Limit work per file
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        # Split by common delimiters
                        line_mod = line.replace(";", ",").replace("\t", ",")
                        tokens = [t.strip() for t in line_mod.split(",") if t.strip()]
                        if not tokens:
                            continue
                        val = None
                        # Try from the end; look for 0/1-like tokens
                        for tok in reversed(tokens):
                            if tok in ("0", "1"):
                                val = int(tok)
                                break
                            low = tok.lower()
                            if low == "true":
                                val = 1
                                break
                            if low == "false":
                                val = 0
                                break
                        if val is None:
                            # Fallback: parse numeric 0/1
                            for tok in reversed(tokens):
                                try:
                                    v = float(tok)
                                except ValueError:
                                    continue
                                if v == 0.0 or v == 1.0:
                                    val = int(v)
                                    break
                        if val is None:
                            continue
                        total += 1
                        if val == 1:
                            avail += 1
            except Exception:
                # If file can't be read or parsed, skip it
                continue

            if total > 0:
                ratio = avail / total
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_idx = idx

        return best_idx

    def _update_work_done_cache(self):
        """Incrementally maintain total work done to avoid repeated full-list sums."""
        # Initialize lazily in case solve wasn't called for some reason
        if not hasattr(self, "_work_done_cache"):
            self._work_done_cache = 0.0
            self._last_num_segments = 0

        segments = self.task_done_time
        n = len(segments)
        last_len = self._last_num_segments
        if n > last_len:
            # Add only new segments
            self._work_done_cache += sum(segments[last_len:n])
            self._last_num_segments = n
        return self._work_done_cache

    def _ensure_region_initialized(self):
        """Switch to preferred region once at the beginning, if available."""
        if getattr(self, "_region_initialized", False):
            return
        self._region_initialized = True
        preferred = getattr(self, "_preferred_region", None)
        try:
            num_regions = self.env.get_num_regions()
            cur_region = self.env.get_current_region()
        except Exception:
            return  # Environment might not support regions as expected

        if (
            preferred is not None
            and isinstance(preferred, int)
            and 0 <= preferred < num_regions
            and preferred != cur_region
        ):
            try:
                self.env.switch_region(preferred)
            except Exception:
                # If switching fails for any reason, just stay in current region
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # Ensure initial region switch (if any)
        self._ensure_region_initialized()

        # Update work done
        work_done = self._update_work_done_cache()
        task_total = getattr(self, "_task_duration_sec", None)
        if task_total is None:
            td = getattr(self, "task_duration", None)
            if isinstance(td, (list, tuple)):
                task_total = float(td[0])
            else:
                task_total = float(td)
            self._task_duration_sec = task_total

        remaining_work = task_total - work_done

        # If task finished, stop using any cluster
        if remaining_work <= 0:
            return ClusterType.NONE

        # Time-related quantities
        elapsed = self.env.elapsed_seconds
        deadline = self.deadline
        time_remaining = deadline - elapsed

        # If already past deadline, further work can't help the score; avoid extra cost
        if time_remaining <= 0:
            return ClusterType.NONE

        # Hard-deadline guarantee via on-demand fallback
        # Commit to ON_DEMAND when remaining time is too short to safely rely on spot or idling.
        gap = getattr(self.env, "gap_seconds", 0.0)
        restart_overhead = self.restart_overhead

        # Safety margin: restart_overhead plus one time step to account for discretization
        safety_time = restart_overhead + gap

        if getattr(self, "_od_committed", False):
            return ClusterType.ON_DEMAND

        if time_remaining <= remaining_work + safety_time:
            # From now on, stay on on-demand until completion to guarantee finishing before deadline
            self._od_committed = True
            return ClusterType.ON_DEMAND

        # Before committing, prefer cheap spot when available; otherwise, wait (NONE)
        if has_spot:
            return ClusterType.SPOT

        # Spot not available and we still have ample slack: wait to avoid expensive on-demand
        return ClusterType.NONE
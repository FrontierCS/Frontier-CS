import json
import os
import math
from argparse import Namespace
from typing import List, Optional

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

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

        # Optional: load traces, if available
        self._use_traces = False
        self._traces: List[List[bool]] = []
        self._run_len: List[List[int]] = []
        self._next_true_offset: List[List[int]] = []
        try:
            trace_files = config.get("trace_files", None)
            if isinstance(trace_files, list) and len(trace_files) > 0:
                self._load_and_precompute_traces(trace_files)
        except Exception:
            # If any issue arises, just fallback to not using traces
            self._use_traces = False
            self._traces = []
            self._run_len = []
            self._next_true_offset = []

        # For exploring regions when we don't use traces
        self._rr_next_region = 0

        # ON_DEMAND commitment flag: once switched to ON_DEMAND, keep it till finish
        self._commit_on_demand = False
        return self

    # ------------------------ Trace utilities ------------------------
    def _parse_trace_file(self, path: str) -> Optional[List[bool]]:
        # Try JSON parsing
        try:
            with open(path, "r") as f:
                content = f.read().strip()
            if not content:
                return None
            # Try JSON first
            try:
                obj = json.loads(content)
                seq = None
                if isinstance(obj, list):
                    seq = obj
                elif isinstance(obj, dict):
                    # Try a few common keys
                    for key in ("availability", "avail", "spot", "data", "values"):
                        if key in obj and isinstance(obj[key], list):
                            seq = obj[key]
                            break
                if seq is not None:
                    return [self._to_bool(x) for x in seq if self._is_valid_token(x)]
            except Exception:
                pass

            # Fallback: parse whitespace / newline separated tokens
            tokens = content.replace(",", " ").split()
            vals = [self._to_bool(tok) for tok in tokens if self._is_valid_token(tok)]
            if len(vals) == 0:
                return None
            return vals
        except Exception:
            return None

    def _is_valid_token(self, x) -> bool:
        if isinstance(x, bool):
            return True
        if isinstance(x, (int, float)):
            return True
        if isinstance(x, str):
            s = x.strip().lower()
            return s in ("1", "0", "true", "false", "t", "f", "yes", "no", "y", "n", "available", "unavailable", "up", "down")
        return False

    def _to_bool(self, x) -> bool:
        if isinstance(x, bool):
            return x
        if isinstance(x, (int, float)):
            return bool(int(x))
        if isinstance(x, str):
            s = x.strip().lower()
            if s in ("1", "true", "t", "yes", "y", "available", "up"):
                return True
            if s in ("0", "false", "f", "no", "n", "unavailable", "down"):
                return False
        # Default
        return False

    def _load_and_precompute_traces(self, trace_files: List[str]) -> None:
        n_regions_env = self.env.get_num_regions()
        parsed: List[List[bool]] = []
        for p in trace_files:
            if not isinstance(p, str):
                continue
            if not os.path.exists(p):
                continue
            arr = self._parse_trace_file(p)
            if arr is not None and len(arr) > 0:
                parsed.append(arr)

        if len(parsed) == 0:
            # Disable traces
            self._use_traces = False
            return

        # Adjust number of regions to env if mismatch
        if len(parsed) >= n_regions_env:
            self._traces = parsed[:n_regions_env]
        else:
            # If fewer traces than regions, replicate last to fill
            # (rare; but better than failing)
            needed = n_regions_env - len(parsed)
            fill = parsed[-1] if parsed else [True]
            self._traces = parsed + [fill[:] for _ in range(needed)]

        # Normalize lengths: ensure each has at least some steps
        min_len = min(len(x) for x in self._traces)
        if min_len == 0:
            self._use_traces = False
            self._traces = []
            return

        # Precompute run-length and next-true-offset for efficient lookup
        self._run_len = []
        self._next_true_offset = []
        for arr in self._traces:
            T = len(arr)
            run = [0] * T
            nxt = [0] * T

            # run-length of consecutive True starting at t
            last_run = 0
            for t in range(T - 1, -1, -1):
                if arr[t]:
                    last_run = last_run + 1
                    run[t] = last_run
                else:
                    last_run = 0
                    run[t] = 0

            # next true offset from t (0 if arr[t] True else minimal k>0 s.t. arr[t+k] True)
            INF = 10**9
            next_offset = INF
            # We'll maintain the distance to the next true at t+1:
            # nxt[t] = 0 if arr[t] else (1 + nxt[t+1] if nxt[t+1] < INF else INF)
            for t in range(T - 1, -1, -1):
                if arr[t]:
                    nxt[t] = 0
                    next_offset = 0
                else:
                    if t == T - 1:
                        nxt[t] = INF
                        next_offset = INF
                    else:
                        nxt_next = nxt[t + 1]
                        nxt[t] = nxt_next + 1 if nxt_next < INF else INF
                        next_offset = nxt[t]
            self._run_len.append(run)
            self._next_true_offset.append(nxt)

        self._use_traces = True

    def _trace_avail(self, region: int, idx: int) -> bool:
        arr = self._traces[region]
        if idx < 0:
            idx = 0
        if idx < len(arr):
            return arr[idx]
        # After end of trace, assume the last state repeats
        return arr[-1]

    def _trace_run_len(self, region: int, idx: int) -> int:
        run = self._run_len[region]
        if idx < 0:
            idx = 0
        if idx < len(run):
            return run[idx]
        # After end, if last entry is True, treat as 1 (unknown future); else 0
        return 1 if self._traces[region][-1] else 0

    def _trace_next_true_offset(self, region: int, idx: int) -> int:
        nxt = self._next_true_offset[region]
        arr = self._traces[region]
        INF = 10**9
        if idx < 0:
            idx = 0
        if idx < len(nxt):
            return nxt[idx]
        # After end: if last is True -> 0, else INF
        return 0 if arr[-1] else INF

    # ------------------------ Strategy ------------------------

    def _remaining_work(self) -> float:
        done = 0.0
        if self.task_done_time:
            # task_done_time: list of completed work segments (seconds)
            for d in self.task_done_time:
                done += d
        return max(0.0, self.task_duration - done)

    def _must_commit_on_demand_now(self, last_cluster_type: ClusterType) -> bool:
        # If already committed, keep using ON_DEMAND
        if self._commit_on_demand:
            return True
        # If currently running ON_DEMAND, keep it
        if last_cluster_type == ClusterType.ON_DEMAND:
            return True

        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        remaining_work = self._remaining_work()
        # To start ON_DEMAND now we pay a restart overhead exactly once
        # Being conservative, include restart_overhead for safety
        required = remaining_work + self.restart_overhead

        # If not enough time to wait even a single step safely, must start now
        return time_left <= required + 1e-6

    def _maybe_commit_on_demand(self, last_cluster_type: ClusterType) -> bool:
        must = self._must_commit_on_demand_now(last_cluster_type)
        if must:
            self._commit_on_demand = True
        return must

    def _pick_best_spot_region_now(self, step_idx: int, current_region: int) -> Optional[int]:
        # If current region already has spot, prefer staying to avoid an extra restart overhead
        if self._trace_avail(current_region, step_idx):
            return current_region
        # Else, choose the region with availability now and the largest continuous run length
        best_region = None
        best_score = -1
        n_regions = self.env.get_num_regions()
        for r in range(n_regions):
            if self._trace_avail(r, step_idx):
                rl = self._trace_run_len(r, step_idx)
                if rl > best_score:
                    best_score = rl
                    best_region = r
        return best_region

    def _best_future_spot_target(self, step_idx: int) -> Optional[int]:
        # Choose the region that will get spot in the fewest steps; tie-break: largest run length after that index
        n_regions = self.env.get_num_regions()
        best_r = None
        best_offset = 10**9
        best_run = -1
        for r in range(n_regions):
            off = self._trace_next_true_offset(r, step_idx)
            if off < best_offset:
                best_offset = off
                # Evaluate run length at that future time
                rl = self._trace_run_len(r, step_idx + off)
                best_run = rl
                best_r = r
            elif off == best_offset:
                rl = self._trace_run_len(r, step_idx + off)
                if rl > best_run:
                    best_run = rl
                    best_r = r
        return best_r

    def _max_wait_steps_safe(self) -> int:
        # Maximum number of full steps we can wait (choose NONE) and still
        # be able to finish on ON_DEMAND afterward by the deadline.
        now = self.env.elapsed_seconds
        time_left = self.deadline - now
        remaining_work = self._remaining_work()
        # Conservative: assume we will need a restart overhead when starting ON_DEMAND
        required = remaining_work + self.restart_overhead
        extra = time_left - required
        if extra <= 0.0:
            return 0
        gap = self.env.gap_seconds
        return max(0, int(math.floor((extra + 1e-9) / gap)))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        # If finished, do nothing
        if self._remaining_work() <= 0.0:
            return ClusterType.NONE

        # If already on ON_DEMAND, keep using it to avoid risk
        if last_cluster_type == ClusterType.ON_DEMAND or self._commit_on_demand:
            self._commit_on_demand = True
            return ClusterType.ON_DEMAND

        # If time is too tight, switch to ON_DEMAND now
        if self._maybe_commit_on_demand(last_cluster_type):
            return ClusterType.ON_DEMAND

        current_region = self.env.get_current_region()
        gap = self.env.gap_seconds
        step_idx = int(self.env.elapsed_seconds // gap)

        # Prefer SPOT when available
        if has_spot:
            return ClusterType.SPOT

        # SPOT not available in current region
        # If traces available, try to pick a region with spot now
        if self._use_traces:
            best_now_region = self._pick_best_spot_region_now(step_idx, current_region)
            if best_now_region is not None and best_now_region != current_region:
                self.env.switch_region(best_now_region)
                # We know spot is available there at this step; use it
                return ClusterType.SPOT
            elif best_now_region == current_region and best_now_region is not None:
                # Shouldn't happen because has_spot is False, but guard anyway
                return ClusterType.SPOT

            # No region has spot at this step; plan to wait if safe
            max_wait = self._max_wait_steps_safe()
            if max_wait >= 1:
                # Choose a target region where spot arrives soonest
                target_region = self._best_future_spot_target(step_idx)
                if target_region is not None and target_region != current_region:
                    self.env.switch_region(target_region)
                return ClusterType.NONE
            else:
                # Cannot wait; must commit to ON_DEMAND now
                self._commit_on_demand = True
                return ClusterType.ON_DEMAND

        # No traces: simple heuristic
        # If we can safely wait, do NONE and rotate regions to increase chance of finding spot next step
        max_wait = self._max_wait_steps_safe()
        if max_wait >= 1:
            # Round-robin region hopping while waiting
            n_regions = self.env.get_num_regions()
            if n_regions > 1:
                self._rr_next_region = (current_region + 1) % n_regions
                if self._rr_next_region != current_region:
                    self.env.switch_region(self._rr_next_region)
            return ClusterType.NONE

        # Otherwise, must commit to ON_DEMAND now
        self._commit_on_demand = True
        return ClusterType.ON_DEMAND
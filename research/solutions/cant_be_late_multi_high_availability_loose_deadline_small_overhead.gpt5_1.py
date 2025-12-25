import json
import os
import math
from argparse import Namespace

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
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

        self._gap = float(self.env.gap_seconds)
        self._overhead = float(self.restart_overhead)
        self._deadline = float(self.deadline)
        self._task_duration = float(self.task_duration)

        self._trace_files = config.get("trace_files", []) or []
        self._pred_enabled = False
        self._region_count = 0
        self._N_steps = max(1, int(math.ceil(self._deadline / self._gap)) + 2)

        self._run_len = []
        self._next_true = []
        self._trace_data = []
        try:
            self._setup_predictions()
        except Exception:
            self._pred_enabled = False
            self._run_len = []
            self._next_true = []
            self._trace_data = []

        self._min_runlen_to_switch = max(
            1, int(math.ceil(self._overhead / max(self._gap, 1e-9))) + 1
        )
        self._switch_hysteresis = 1
        return self

    def _setup_predictions(self):
        if not self._trace_files:
            self._pred_enabled = False
            return
        parsed = []
        for p in self._trace_files:
            arr = self._parse_trace_file(p)
            if arr is None or len(arr) == 0:
                parsed.append(None)
            else:
                parsed.append([bool(x) for x in arr])

        # Determine number of regions to use (min of env and parsed)
        env_regions = 0
        try:
            env_regions = int(self.env.get_num_regions())
        except Exception:
            env_regions = len([a for a in parsed if a is not None]) or len(parsed)

        regions_use = min(env_regions if env_regions > 0 else len(parsed), len(parsed))
        self._region_count = regions_use

        # Prepare data for each region; expand/trim to N steps
        self._trace_data = []
        for i in range(self._region_count):
            base = parsed[i] if i < len(parsed) else None
            if base is None or len(base) == 0:
                self._trace_data.append(None)
            else:
                if len(base) >= self._N_steps:
                    data = base[: self._N_steps]
                else:
                    # Repeat pattern to fill
                    times = self._N_steps // len(base)
                    rem = self._N_steps % len(base)
                    data = base * max(1, times) + base[:rem]
                    data = data[: self._N_steps]
                self._trace_data.append(data)

        # If too many None, disable predictions
        valid_count = sum(1 for x in self._trace_data if x is not None)
        if valid_count == 0:
            self._pred_enabled = False
            return

        # Precompute run lengths and next_true arrays
        self._run_len = []
        self._next_true = []
        for i in range(self._region_count):
            arr = self._trace_data[i]
            if arr is None:
                self._run_len.append([0] * self._N_steps)
                self._next_true.append([-1] * self._N_steps)
                continue
            N = self._N_steps
            runlen = [0] * N
            nexttrue = [-1] * N
            cnt = 0
            nxt = -1
            for idx in range(N - 1, -1, -1):
                if arr[idx]:
                    cnt += 1
                    nxt = idx
                else:
                    cnt = 0
                runlen[idx] = cnt
                nexttrue[idx] = nxt
            self._run_len.append(runlen)
            self._next_true.append(nexttrue)

        self._pred_enabled = True

    def _parse_trace_file(self, path):
        try:
            if not os.path.isfile(path):
                return None
            # Try JSON
            with open(path, "r") as f:
                content = f.read().strip()
            if not content:
                return None
            # Attempt JSON parse
            arr = None
            try:
                data = json.loads(content)
                if isinstance(data, list):
                    arr = self._coerce_list_to_bool_list(data)
                elif isinstance(data, dict):
                    # Look for list-like values
                    best = None
                    best_len = -1
                    for v in data.values():
                        if isinstance(v, list) and len(v) > best_len:
                            best_len = len(v)
                            best = v
                    if best is not None:
                        arr = self._coerce_list_to_bool_list(best)
                if arr is not None:
                    return arr
            except Exception:
                pass

            # Fallback: parse lines
            lines = content.splitlines()
            out = []
            for line in lines:
                s = line.strip()
                if not s:
                    continue
                if s.startswith("#"):
                    continue
                # Try single number/token per line
                token = s
                # If CSV or space-separated, pick last token
                if "," in s:
                    parts = [p.strip() for p in s.split(",") if p.strip()]
                    if parts:
                        token = parts[-1]
                elif " " in s or "\t" in s:
                    parts = [p.strip() for p in s.replace("\t", " ").split(" ") if p.strip()]
                    if parts:
                        token = parts[-1]
                val = self._parse_bool_token(token)
                if val is not None:
                    out.append(val)
                else:
                    # Try scanning for first 0/1 in the tokens
                    tokens = []
                    if "," in s:
                        tokens = [p.strip() for p in s.split(",")]
                    elif " " in s or "\t" in s:
                        tokens = [p.strip() for p in s.replace("\t", " ").split(" ")]
                    for t in tokens:
                        v2 = self._parse_bool_token(t)
                        if v2 is not None:
                            out.append(v2)
                            break
            return out if out else None
        except Exception:
            return None

    def _coerce_list_to_bool_list(self, lst):
        out = []
        for x in lst:
            if isinstance(x, bool):
                out.append(x)
            elif isinstance(x, (int, float)):
                out.append(bool(int(x)))
            elif isinstance(x, str):
                v = self._parse_bool_token(x)
                if v is not None:
                    out.append(v)
            else:
                # unknown
                pass
        return out

    def _parse_bool_token(self, token):
        t = token.strip().lower()
        if t in ("1", "true", "t", "yes", "y", "available", "up"):
            return True
        if t in ("0", "false", "f", "no", "n", "down", "unavailable"):
            return False
        try:
            n = float(t)
            return bool(int(n))
        except Exception:
            return None

    def _best_spot_region_now(self, step_idx):
        best_region = None
        best_len = 0
        R = min(self._region_count, self.env.get_num_regions())
        for r in range(R):
            if self._trace_data[r] is None:
                continue
            if step_idx < self._N_steps:
                L = self._run_len[r][step_idx]
                if L > best_len:
                    best_len = L
                    best_region = r
        return best_region, best_len

    def _earliest_spot_future(self, step_idx):
        min_wait = None
        region = None
        R = min(self._region_count, self.env.get_num_regions())
        for r in range(R):
            if self._trace_data[r] is None:
                continue
            if step_idx < self._N_steps:
                nxt = self._next_true[r][step_idx]
                if nxt >= 0:
                    wait = nxt - step_idx
                    if min_wait is None or wait < min_wait:
                        min_wait = wait
                        region = r
        return min_wait, region

    def _current_region_runlen(self, step_idx, has_spot):
        r = self.env.get_current_region()
        if self._pred_enabled and r < self._region_count and self._trace_data[r] is not None and step_idx < self._N_steps:
            return self._run_len[r][step_idx]
        return 1 if has_spot else 0

    def _should_force_on_demand(self, time_left, remaining):
        # Safety buffer to ensure completion on time
        # Choose a conservative buffer relative to gap and overhead.
        buffer_time = max(3 * self._gap, 6 * self._overhead)
        return (time_left - remaining) <= buffer_time

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        elapsed = float(self.env.elapsed_seconds)
        time_left = self._deadline - elapsed
        if time_left <= 0.0:
            return ClusterType.NONE

        done = sum(self.task_done_time) if self.task_done_time else 0.0
        remaining = max(0.0, self._task_duration - done)
        if remaining <= 0.0:
            return ClusterType.NONE

        if self._should_force_on_demand(time_left, remaining):
            return ClusterType.ON_DEMAND

        step_idx = int(elapsed // max(self._gap, 1e-9))

        # If predictions are available, use them to select best region
        if self._pred_enabled:
            # Select region with the longest current availability run
            best_region, best_len = self._best_spot_region_now(step_idx)
            curr_len = self._current_region_runlen(step_idx, has_spot)

            if best_len > 0:
                # Spot is available somewhere now
                curr_region = self.env.get_current_region()
                # If already on SPOT and current region has spot now, prefer to stay
                if last_cluster_type == ClusterType.SPOT and curr_len > 0 and has_spot:
                    # Only switch if there is a significantly better run ahead
                    if best_region is not None and best_region != curr_region:
                        # Switch only if we gain sufficiently more steps
                        if (best_len - curr_len) >= (self._min_runlen_to_switch + self._switch_hysteresis):
                            if (time_left - remaining) > self._overhead:
                                self.env.switch_region(best_region)
                                return ClusterType.SPOT
                    return ClusterType.SPOT
                else:
                    # Not currently on SPOT or no spot in current region; switch if worthwhile
                    target_region = best_region if best_region is not None else curr_region
                    # Ensure predicted spot available at target
                    if target_region is not None and best_len >= 1:
                        # If switching cluster type (from OD/NONE) incurs overhead, ensure slack is enough
                        # Slack = time_left - remaining
                        slack = time_left - remaining
                        overhead_needed = self._overhead if last_cluster_type != ClusterType.SPOT else 0.0
                        # Require some minimum run before switching to spot
                        min_run_needed = max(self._min_runlen_to_switch, 1)
                        if best_len >= min_run_needed and slack > overhead_needed:
                            if target_region != curr_region:
                                self.env.switch_region(target_region)
                            return ClusterType.SPOT
                        # If we cannot justify switching, consider idling briefly if safe and soon another spot will appear
                        # fallthrough below to wait logic
            # No spot anywhere this step; consider waiting or on-demand
            wait_steps, wait_region = self._earliest_spot_future(step_idx)
            if wait_steps is not None:
                wait_time = wait_steps * self._gap
                # If we have enough slack to wait for next spot, choose NONE (idle)
                # Reserve additional buffer to account for overhead when we switch to run
                reserve = max(2 * self._gap, 3 * self._overhead)
                if (time_left - remaining) > (wait_time + reserve):
                    return ClusterType.NONE
            # Not enough slack to wait; go on-demand
            return ClusterType.ON_DEMAND

        # Fallback when we don't have predictions: simple heuristic using has_spot
        if has_spot:
            return ClusterType.SPOT

        # No spot in current region; if there is enough slack, wait; else on-demand
        slack_simple = time_left - remaining
        if slack_simple > (max(2 * self._gap, 3 * self._overhead)):
            return ClusterType.NONE
        return ClusterType.ON_DEMAND

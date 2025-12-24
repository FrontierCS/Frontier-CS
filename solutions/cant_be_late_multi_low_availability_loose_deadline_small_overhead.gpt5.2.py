import json
import math
import os
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "trace_aware_deadline_guard_v1"

    _SPOT_PRICE_PER_HOUR = 0.9701
    _ON_DEMAND_PRICE_PER_HOUR = 3.06

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        self._spec_config = config
        self._trace_paths = list(config.get("trace_files", [])) if isinstance(config.get("trace_files", []), list) else []
        self._traces_initialized = False

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._task_duration_seconds = float(self.task_duration[0] if isinstance(self.task_duration, (list, tuple)) else self.task_duration)
        self._deadline_seconds = float(self.deadline[0] if isinstance(self.deadline, (list, tuple)) else self.deadline)
        self._restart_overhead_seconds = float(self.restart_overhead[0] if isinstance(self.restart_overhead, (list, tuple)) else self.restart_overhead)

        self._work_done = 0.0
        self._last_done_len = 0

        self._committed_ondemand = False

        return self

    def _maybe_init_traces(self) -> None:
        if self._traces_initialized:
            return

        self._traces_initialized = True
        self._use_traces = False

        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = 0

        if num_regions <= 0 or not self._trace_paths:
            return

        if len(self._trace_paths) < num_regions:
            # If fewer paths than regions, don't attempt multi-region trace logic.
            return

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if gap <= 0:
            return

        self._gap_seconds = gap
        self._horizon_steps = int(math.ceil(self._deadline_seconds / self._gap_seconds)) + 5

        avail_by_region: List[bytearray] = []
        for r in range(num_regions):
            path = self._trace_paths[r]
            data = self._parse_trace_to_bytearray(path)
            if data is None or len(data) == 0:
                return
            if len(data) < self._horizon_steps:
                data.extend(b"\x00" * (self._horizon_steps - len(data)))
            elif len(data) > self._horizon_steps:
                data = data[: self._horizon_steps]
            avail_by_region.append(data)

        runlen_by_region: List[array] = []
        for r in range(num_regions):
            av = avail_by_region[r]
            n = len(av)
            rl = array("I", [0]) * (n + 1)
            # reverse compute consecutive ones
            for i in range(n - 1, -1, -1):
                if av[i]:
                    rl[i] = rl[i + 1] + 1
                else:
                    rl[i] = 0
            runlen_by_region.append(rl)

        self._avail_by_region = avail_by_region
        self._runlen_by_region = runlen_by_region
        self._num_regions = num_regions

        # Minimum run length to be cheaper than on-demand per effective work when starting a fresh spot run.
        o = float(self._restart_overhead_seconds)
        p_s = float(self._SPOT_PRICE_PER_HOUR)
        p_o = float(self._ON_DEMAND_PRICE_PER_HOUR)
        denom = (p_o - p_s)
        if denom <= 1e-12:
            self._min_run_steps = 1
        else:
            required_secs = o * p_o / denom
            self._min_run_steps = max(1, int(math.ceil(required_secs / self._gap_seconds)))

        # Offset inference for trace index alignment with env steps.
        self._offset_candidates = (-3, -2, -1, 0, 1, 2, 3)
        self._offset_scores: Dict[int, int] = {c: 0 for c in self._offset_candidates}
        self._offset_obs = 0
        self._best_offset = 0
        self._plausible_offsets: Tuple[int, ...] = self._offset_candidates
        self._trace_confident = False
        self._trace_mismatch_strikes = 0

        self._use_traces = True

    @staticmethod
    def _extract_list_from_json_obj(obj: Any) -> Optional[List[Any]]:
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            for k in ("availability", "avail", "spot", "trace", "data", "values"):
                v = obj.get(k, None)
                if isinstance(v, list):
                    return v
            # Maybe nested dict
            for v in obj.values():
                if isinstance(v, list):
                    return v
                if isinstance(v, dict):
                    vv = Solution._extract_list_from_json_obj(v)
                    if vv is not None:
                        return vv
        return None

    def _parse_trace_to_bytearray(self, path: str) -> Optional[bytearray]:
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except Exception:
            return None

        if not raw:
            return None

        # NPY format
        if raw.startswith(b"\x93NUMPY"):
            try:
                import numpy as np  # type: ignore

                arr = np.load(path, allow_pickle=False)
                flat = arr.reshape(-1)
                out = bytearray(len(flat))
                # Accept bool/int/float
                for i, v in enumerate(flat):
                    out[i] = 1 if bool(v) else 0
                return out
            except Exception:
                pass

        # JSON format
        stripped = raw.lstrip()
        if stripped.startswith(b"{") or stripped.startswith(b"["):
            try:
                text = raw.decode("utf-8", errors="strict")
                obj = json.loads(text)
                lst = self._extract_list_from_json_obj(obj)
                if lst is None:
                    return None
                out = bytearray(len(lst))
                for i, v in enumerate(lst):
                    if isinstance(v, bool):
                        out[i] = 1 if v else 0
                    elif isinstance(v, (int, float)):
                        out[i] = 1 if v != 0 else 0
                    elif isinstance(v, str):
                        vv = v.strip().lower()
                        if vv in ("1", "true", "t", "yes", "y"):
                            out[i] = 1
                        elif vv in ("0", "false", "f", "no", "n"):
                            out[i] = 0
                        else:
                            # Unknown token: treat as 0
                            out[i] = 0
                    else:
                        out[i] = 0
                return out
            except Exception:
                pass

        # Text/CSV format
        try:
            text = raw.decode("utf-8", errors="ignore")
        except Exception:
            return None

        out = bytearray()
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("#"):
                continue
            # Remove common separators
            parts = line.replace(",", " ").replace("\t", " ").split()
            if not parts:
                continue
            # Find last parsable 0/1/true/false token
            tok = None
            for p in reversed(parts):
                pp = p.strip().lower()
                if pp in ("0", "1", "true", "false", "t", "f", "yes", "no", "y", "n"):
                    tok = pp
                    break
            if tok is None:
                continue
            if tok in ("1", "true", "t", "yes", "y"):
                out.append(1)
            else:
                out.append(0)

        if len(out) == 0:
            # Fallback: token-scan whole file
            tokens = text.replace(",", " ").replace("\t", " ").split()
            for t in tokens:
                tt = t.strip().lower()
                if tt in ("0", "1"):
                    out.append(1 if tt == "1" else 0)

        return out if len(out) else None

    def _update_work_done(self) -> None:
        td = self.task_done_time
        n = len(td)
        if n <= self._last_done_len:
            return
        # Usually only one new entry per step; keep it general.
        for i in range(self._last_done_len, n):
            try:
                self._work_done += float(td[i])
            except Exception:
                pass
        self._last_done_len = n

    def _env_step_index(self) -> int:
        g = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        e = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        # elapsed_seconds should be multiple of g at step boundaries; floor is fine.
        return int((e / g) + 1e-9)

    def _update_offset_inference(self, env_step: int, region: int, has_spot: bool) -> None:
        if not self._use_traces:
            return
        av = self._avail_by_region[region]
        n = len(av)

        self._offset_obs += 1
        for c in self._offset_candidates:
            idx = env_step + c
            if 0 <= idx < n:
                if bool(av[idx]) == bool(has_spot):
                    self._offset_scores[c] += 1

        # Determine best and plausible offsets
        best_c = max(self._offset_candidates, key=lambda x: self._offset_scores[x])
        best_s = self._offset_scores[best_c]
        # plausible: within 1 match of best
        plausible = [c for c in self._offset_candidates if (best_s - self._offset_scores[c]) <= 1]

        self._best_offset = best_c
        self._plausible_offsets = tuple(plausible)

        # Confidence criterion
        # - early: require at least 4 obs and unique best
        # - later: lock in after 12 obs
        if self._offset_obs >= 12:
            self._trace_confident = True
            self._plausible_offsets = (best_c,)
        elif self._offset_obs >= 4:
            # unique best and strong consistency
            second_s = max(self._offset_scores[c] for c in self._offset_candidates if c != best_c)
            if best_s - second_s >= 2:
                self._trace_confident = True
                self._plausible_offsets = (best_c,)

        # If "confident", validate current step; if mismatch, strike
        if self._trace_confident:
            idx = env_step + self._best_offset
            pred = None
            if 0 <= idx < n:
                pred = bool(av[idx])
            if pred is None or pred != bool(has_spot):
                self._trace_mismatch_strikes += 1
                if self._trace_mismatch_strikes >= 2:
                    # Disable to avoid invalid SPOT decisions across regions.
                    self._use_traces = False

    def _select_spot_region(self, env_step: int) -> Tuple[int, int]:
        # Returns (region_idx, runlen_steps) or (-1, 0) if none safe.
        if not self._use_traces:
            return -1, 0
        plausible = self._plausible_offsets
        if not plausible:
            plausible = (self._best_offset,)

        best_r = -1
        best_min_run = 0
        cur_r = int(self.env.get_current_region())

        for r in range(self._num_regions):
            rl_arr = self._runlen_by_region[r]
            # Require availability across all plausible offsets
            min_run = 1 << 30
            ok = True
            for off in plausible:
                idx = env_step + off
                if idx < 0 or idx >= len(rl_arr) - 1:
                    ok = False
                    break
                rl = int(rl_arr[idx])
                if rl <= 0:
                    ok = False
                    break
                if rl < min_run:
                    min_run = rl
            if not ok:
                continue

            if min_run > best_min_run:
                best_min_run = min_run
                best_r = r
            elif min_run == best_min_run and min_run > 0:
                # Prefer staying in current region to reduce restarts.
                if r == cur_r and best_r != cur_r:
                    best_r = r

        return best_r, best_min_run if best_r >= 0 else 0

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._maybe_init_traces()
        self._update_work_done()

        remaining_work = self._task_duration_seconds - self._work_done
        if remaining_work <= 0:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        remaining_time = self._deadline_seconds - elapsed

        g = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        o = float(self._restart_overhead_seconds)

        # Safety margin: enough to absorb a few restarts / step-granularity.
        safety_margin = max(10.0 * g, 5.0 * o)
        if safety_margin > 10800.0:
            safety_margin = 10800.0

        if self._committed_ondemand:
            return ClusterType.ON_DEMAND

        # If we must guarantee finishing, commit to on-demand and never leave.
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_needed = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        else:
            overhead_needed = o
        if remaining_time <= (remaining_work + overhead_needed + safety_margin):
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        # Spot continuation is always good if already running spot and still available.
        if last_cluster_type == ClusterType.SPOT and has_spot:
            return ClusterType.SPOT

        # If traces available, use them to select a safe region with long spot run.
        env_step = self._env_step_index()
        cur_region = int(self.env.get_current_region())

        if self._use_traces:
            self._update_offset_inference(env_step, cur_region, has_spot)

        # If we can't trust traces, fall back to local info (no switching).
        if not self._use_traces:
            if has_spot:
                return ClusterType.SPOT
            return ClusterType.NONE

        # If we can spot now safely in some region, prefer starting only if run is long enough.
        best_r, best_run = self._select_spot_region(env_step)

        if best_r >= 0 and best_run >= int(self._min_run_steps):
            if best_r != cur_region:
                try:
                    self.env.switch_region(best_r)
                    cur_region = best_r
                except Exception:
                    # If switching fails, don't risk SPOT.
                    return ClusterType.NONE
            return ClusterType.SPOT

        # If current region has spot, it's safe to run spot even if we don't have a guaranteed long run.
        if has_spot:
            return ClusterType.SPOT

        return ClusterType.NONE

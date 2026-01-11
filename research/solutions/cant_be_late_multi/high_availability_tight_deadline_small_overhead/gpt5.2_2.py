import os
import json
import math
from array import array
from argparse import Namespace
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _as_float_scalar(x: Any) -> float:
    if isinstance(x, (list, tuple)) and x:
        return float(x[0])
    return float(x)


def _is_boolish_true(s: str) -> bool:
    sl = s.strip().lower()
    return sl in ("1", "true", "t", "yes", "y", "on")


def _parse_trace_file(path: str) -> Optional[Union[List[int], Tuple[List[float], List[int]]]]:
    # Returns either:
    # - list[int] availability (0/1) per record, or
    # - (times, values) where times are floats and values are 0/1
    try:
        with open(path, "rb") as f:
            head = f.read(16)
        if head.startswith(b"\x93NUMPY"):
            try:
                import numpy as np  # type: ignore

                arr = np.load(path, allow_pickle=False)
                arr = arr.reshape(-1)
                vals = []
                for v in arr.tolist():
                    try:
                        fv = float(v)
                        vals.append(1 if fv > 0 else 0)
                    except Exception:
                        vals.append(1 if bool(v) else 0)
                return vals
            except Exception:
                return None

        with open(path, "r", encoding="utf-8") as f:
            txt = f.read().strip()
        if not txt:
            return None

        if txt[0] in "[{":
            try:
                obj = json.loads(txt)
            except Exception:
                obj = None
            if obj is None:
                return None

            if isinstance(obj, list):
                if not obj:
                    return []
                if isinstance(obj[0], (list, tuple)) and len(obj[0]) >= 2:
                    times: List[float] = []
                    vals: List[int] = []
                    for row in obj:
                        try:
                            t = float(row[0])
                            v = row[1]
                            if isinstance(v, str):
                                iv = 1 if _is_boolish_true(v) else 0
                            else:
                                iv = 1 if float(v) > 0 else 0
                            times.append(t)
                            vals.append(iv)
                        except Exception:
                            continue
                    if times and vals and len(times) == len(vals):
                        return (times, vals)
                    return None
                vals = []
                for v in obj:
                    try:
                        if isinstance(v, str):
                            vals.append(1 if _is_boolish_true(v) else 0)
                        else:
                            vals.append(1 if float(v) > 0 else 0)
                    except Exception:
                        vals.append(1 if bool(v) else 0)
                return vals

            if isinstance(obj, dict):
                # Try common keys
                candidates = [
                    ("timestamps", "availability"),
                    ("times", "availability"),
                    ("time", "availability"),
                    ("timestamp", "available"),
                    ("t", "v"),
                    ("x", "y"),
                ]
                for tk, vk in candidates:
                    if tk in obj and vk in obj:
                        try:
                            times_raw = obj[tk]
                            vals_raw = obj[vk]
                            if isinstance(times_raw, list) and isinstance(vals_raw, list):
                                n = min(len(times_raw), len(vals_raw))
                                times = []
                                vals = []
                                for i in range(n):
                                    try:
                                        t = float(times_raw[i])
                                        v = vals_raw[i]
                                        if isinstance(v, str):
                                            iv = 1 if _is_boolish_true(v) else 0
                                        else:
                                            iv = 1 if float(v) > 0 else 0
                                        times.append(t)
                                        vals.append(iv)
                                    except Exception:
                                        continue
                                if times and vals:
                                    return (times, vals)
                        except Exception:
                            pass

                # If dict contains a list under some key, try it
                for k, v in obj.items():
                    if isinstance(v, list) and v:
                        if isinstance(v[0], (int, float, str, bool)):
                            vals = []
                            for x in v:
                                try:
                                    if isinstance(x, str):
                                        vals.append(1 if _is_boolish_true(x) else 0)
                                    else:
                                        vals.append(1 if float(x) > 0 else 0)
                                except Exception:
                                    vals.append(1 if bool(x) else 0)
                            return vals
                        if isinstance(v[0], (list, tuple)) and len(v[0]) >= 2:
                            times = []
                            vals = []
                            for row in v:
                                try:
                                    t = float(row[0])
                                    x = row[1]
                                    if isinstance(x, str):
                                        iv = 1 if _is_boolish_true(x) else 0
                                    else:
                                        iv = 1 if float(x) > 0 else 0
                                    times.append(t)
                                    vals.append(iv)
                                except Exception:
                                    continue
                            if times and vals:
                                return (times, vals)
                return None

        # Text / CSV-like
        lines = txt.splitlines()
        times: List[float] = []
        vals: List[int] = []
        vals_only: List[int] = []
        parsed_pairs = 0
        parsed_single = 0

        for line in lines:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("//"):
                continue
            # Remove possible trailing comments
            if "#" in s:
                s = s.split("#", 1)[0].strip()
                if not s:
                    continue
            if "," in s:
                parts = [p.strip() for p in s.split(",") if p.strip() != ""]
            else:
                parts = [p for p in s.split() if p]
            if not parts:
                continue

            # Skip headers
            if any(ch.isalpha() for ch in parts[0]) and len(parts) >= 2 and any(ch.isalpha() for ch in parts[1]):
                continue

            if len(parts) >= 2:
                try:
                    t = float(parts[0])
                    v = parts[1]
                    if isinstance(v, str):
                        iv = 1 if _is_boolish_true(v) else (1 if float(v) > 0 else 0)
                    else:
                        iv = 1 if float(v) > 0 else 0
                    times.append(t)
                    vals.append(iv)
                    parsed_pairs += 1
                    continue
                except Exception:
                    pass

            # single value
            try:
                v = parts[0]
                if isinstance(v, str):
                    iv = 1 if _is_boolish_true(v) else (1 if float(v) > 0 else 0)
                else:
                    iv = 1 if float(v) > 0 else 0
                vals_only.append(iv)
                parsed_single += 1
            except Exception:
                continue

        if parsed_pairs >= max(5, parsed_single // 2) and parsed_pairs > 0:
            return (times, vals)
        if parsed_single > 0:
            return vals_only
        return None
    except Exception:
        return None


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_region_v1"

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

        self._spec_dir = os.path.dirname(os.path.abspath(spec_path))
        trace_files = config.get("trace_files", []) or []
        self._trace_paths: List[str] = []
        for p in trace_files:
            if not isinstance(p, str):
                continue
            if os.path.isabs(p):
                self._trace_paths.append(p)
            else:
                self._trace_paths.append(os.path.join(self._spec_dir, p))

        self._raw_traces: List[Optional[Union[List[int], Tuple[List[float], List[int]]]]] = []
        for p in self._trace_paths:
            self._raw_traces.append(_parse_trace_file(p))

        self._initialized = False
        self._trace_ready = False
        self._use_traces = False

        self._avail: List[bytearray] = []
        self._streak: List[array] = []
        self._next_spot: List[array] = []
        self._any_spot: Optional[bytearray] = None
        self._next_any_spot: Optional[array] = None

        self._td_len = 0
        self._work_done = 0.0

        self._trace_check_count = 0
        self._trace_mismatch_count = 0
        self._trace_check_limit = 200
        self._trace_mismatch_limit_rate = 0.15

        self._last_wait_target_region: Optional[int] = None
        return self

    def _init_trace_structures(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = 1

        gap = float(getattr(self.env, "gap_seconds", 1.0))
        deadline = _as_float_scalar(getattr(self, "deadline", 0.0))
        horizon_steps = int(math.ceil(deadline / gap)) + 5
        if horizon_steps < 1:
            horizon_steps = 1

        self._trace_ready = False
        self._use_traces = False
        self._avail = [bytearray(horizon_steps) for _ in range(num_regions)]
        self._streak = [array("I", [0]) * horizon_steps for _ in range(num_regions)]
        self._next_spot = [array("I", [0]) * horizon_steps for _ in range(num_regions)]
        self._any_spot = bytearray(horizon_steps)
        self._next_any_spot = array("I", [0]) * horizon_steps

        if not self._raw_traces:
            return

        sentinel = horizon_steps + 1

        for r in range(num_regions):
            raw = self._raw_traces[r] if r < len(self._raw_traces) else None
            if raw is None:
                continue

            dest = self._avail[r]

            if isinstance(raw, tuple):
                times, vals = raw
                if not times or not vals:
                    continue

                # Normalize and possibly scale timestamps
                t0 = float(times[0])
                norm_times = [float(t) - t0 for t in times]
                max_t = max(norm_times) if norm_times else 0.0

                if max_t > 10.0 * deadline and deadline > 0:
                    norm_times = [t / 1000.0 for t in norm_times]
                    max_t = max(norm_times) if norm_times else 0.0

                # Ensure non-decreasing order; if not, fall back to per-index
                nondecreasing = True
                last = norm_times[0]
                for tt in norm_times[1:]:
                    if tt < last:
                        nondecreasing = False
                        break
                    last = tt

                if not nondecreasing:
                    n = min(len(vals), horizon_steps)
                    for i in range(n):
                        dest[i] = 1 if vals[i] else 0
                else:
                    j = 0
                    nsrc = len(norm_times)
                    for k in range(horizon_steps):
                        t = k * gap
                        while j + 1 < nsrc and norm_times[j + 1] <= t:
                            j += 1
                        v = vals[j]
                        dest[k] = 1 if v else 0
            else:
                vals = raw
                n = min(len(vals), horizon_steps)
                for i in range(n):
                    dest[i] = 1 if vals[i] else 0

        # Precompute streaks and next spot
        for r in range(num_regions):
            dest = self._avail[r]
            streak = self._streak[r]
            next_sp = self._next_spot[r]

            nxt = sentinel
            run = 0
            for t in range(horizon_steps - 1, -1, -1):
                if dest[t]:
                    run += 1
                    nxt = t
                else:
                    run = 0
                streak[t] = run
                next_sp[t] = nxt

        # any_spot and next_any_spot
        any_sp = self._any_spot
        next_any = self._next_any_spot
        for t in range(horizon_steps):
            v = 0
            for r in range(num_regions):
                if self._avail[r][t]:
                    v = 1
                    break
            any_sp[t] = v

        nxt = sentinel
        for t in range(horizon_steps - 1, -1, -1):
            if any_sp[t]:
                nxt = t
            next_any[t] = nxt

        self._trace_ready = True
        self._use_traces = False  # enable after sanity checks

    def _update_work_done(self) -> None:
        td = getattr(self, "task_done_time", None)
        if not td:
            return
        l = len(td)
        if l <= self._td_len:
            return
        self._work_done += sum(td[self._td_len : l])
        self._td_len = l

    def _time_index(self) -> int:
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            return 0
        return int(float(getattr(self.env, "elapsed_seconds", 0.0)) // gap)

    def _best_region_to_wait_for_spot(self, t: int) -> Optional[int]:
        if not (self._trace_ready and self._next_spot):
            return None
        num_regions = len(self._next_spot)
        if num_regions <= 0:
            return None
        sentinel = len(self._any_spot) + 1 if self._any_spot is not None else 10**9

        best_r = 0
        best_next = sentinel
        best_streak = 0
        for r in range(num_regions):
            ns = self._next_spot[r]
            n = ns[t] if 0 <= t < len(ns) else sentinel
            if n < best_next:
                best_next = n
                best_r = r
                best_streak = 0
                if n < sentinel and 0 <= n < len(self._streak[r]):
                    best_streak = self._streak[r][n]
            elif n == best_next:
                st = 0
                if n < sentinel and 0 <= n < len(self._streak[r]):
                    st = self._streak[r][n]
                if st > best_streak:
                    best_streak = st
                    best_r = r
        return best_r

    def _sanity_check_trace_alignment(self, t: int, current_region: int, has_spot: bool) -> None:
        if not self._trace_ready or self._use_traces:
            return
        if self._trace_check_count >= self._trace_check_limit:
            # decide whether to trust traces
            if self._trace_check_count > 0:
                rate = self._trace_mismatch_count / float(self._trace_check_count)
                self._use_traces = rate <= self._trace_mismatch_limit_rate
            else:
                self._use_traces = False
            return

        if 0 <= current_region < len(self._avail) and 0 <= t < len(self._avail[current_region]):
            pred = bool(self._avail[current_region][t])
            if pred != bool(has_spot):
                self._trace_mismatch_count += 1
            self._trace_check_count += 1

        if self._trace_check_count >= self._trace_check_limit:
            rate = self._trace_mismatch_count / float(self._trace_check_count)
            self._use_traces = rate <= self._trace_mismatch_limit_rate

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._init_trace_structures()
        self._update_work_done()

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        task_duration = _as_float_scalar(getattr(self, "task_duration", 0.0))
        deadline = _as_float_scalar(getattr(self, "deadline", 0.0))
        restart_overhead = _as_float_scalar(getattr(self, "restart_overhead", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            gap = 1.0

        remaining_work = task_duration - float(self._work_done)
        if remaining_work <= 0:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0:
            return ClusterType.ON_DEMAND

        slack = remaining_time - remaining_work

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        t = self._time_index()
        self._sanity_check_trace_alignment(t, cur_region, has_spot)

        # Panic mode: ensure completion.
        # Avoid pausing/switching when too close to deadline.
        if remaining_time <= remaining_work + 2.0 * restart_overhead + gap:
            return ClusterType.ON_DEMAND

        rro = float(getattr(self, "remaining_restart_overhead", 0.0))
        if rro > 0:
            if last_cluster_type == ClusterType.SPOT and not has_spot:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.NONE:
                return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND
            return last_cluster_type

        # If spot available, generally run spot unless switching from ON_DEMAND is too risky time-wise.
        if has_spot:
            self._last_wait_target_region = None
            if last_cluster_type == ClusterType.ON_DEMAND and slack < 1.2 * restart_overhead:
                return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        # No spot in current region.
        if slack <= 0:
            return ClusterType.ON_DEMAND

        # Decide whether to wait (NONE) vs use ON_DEMAND.
        # Waiting is beneficial to avoid ON_DEMAND cost, but must preserve enough slack.
        if self._use_traces and self._trace_ready and self._best_region_to_wait_for_spot is not None:
            # Switch regions only when we choose to wait (NONE), to avoid paying overhead while computing.
            best_r = self._best_region_to_wait_for_spot(t)
            wait_steps = None
            if best_r is not None and 0 <= best_r < len(self._next_spot):
                sentinel = (len(self._any_spot) + 1) if self._any_spot is not None else (10**9)
                nidx = self._next_spot[best_r][t] if 0 <= t < len(self._next_spot[best_r]) else sentinel
                if nidx >= sentinel:
                    wait_steps = None
                else:
                    # At least one step since we cannot return SPOT in a step where has_spot is False.
                    wait_steps = max(1, int(nidx - t))
            if wait_steps is None:
                # No more spot expected -> ON_DEMAND
                return ClusterType.ON_DEMAND

            wait_time = wait_steps * gap
            if slack >= wait_time + restart_overhead:
                if best_r is not None and best_r != cur_region:
                    if self._last_wait_target_region != best_r:
                        try:
                            self.env.switch_region(best_r)
                        except Exception:
                            pass
                        self._last_wait_target_region = best_r
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        # Fallback (no trusted trace info): wait if there is enough slack to skip a full step.
        if slack >= gap + restart_overhead:
            return ClusterType.NONE
        return ClusterType.ON_DEMAND
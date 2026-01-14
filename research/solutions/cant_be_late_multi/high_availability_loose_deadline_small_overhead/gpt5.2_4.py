import json
import math
import os
import gzip
import pickle
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_SPOT_PRICE = 0.9701
_OD_PRICE = 3.06


def _as_scalar(v: Any) -> float:
    if isinstance(v, (list, tuple)):
        return float(v[0])
    return float(v)


def _read_file_bytes(path: str) -> bytes:
    if path.endswith(".gz"):
        with gzip.open(path, "rb") as f:
            return f.read()
    with open(path, "rb") as f:
        return f.read()


def _extract_trace_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        for k in ("trace", "availability", "avail", "has_spot", "spot", "data", "series", "values"):
            if k in obj:
                return obj[k]
    return obj


def _to_bool(x: Any) -> int:
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float)):
        return 1 if float(x) > 0.5 else 0
    if isinstance(x, str):
        s = x.strip().lower()
        if s in ("1", "true", "t", "yes", "y", "on"):
            return 1
        if s in ("0", "false", "f", "no", "n", "off", ""):
            return 0
        try:
            return 1 if float(s) > 0.5 else 0
        except Exception:
            return 0
    if isinstance(x, dict):
        for k in ("availability", "avail", "has_spot", "spot", "available", "is_available"):
            if k in x:
                return _to_bool(x[k])
        if x:
            return _to_bool(next(iter(x.values())))
        return 0
    if isinstance(x, (list, tuple)) and x:
        return _to_bool(x[-1])
    return 0


def _parse_trace_file(path: str) -> bytearray:
    data = _read_file_bytes(path)
    if not data:
        return bytearray()

    if path.endswith(".pkl") or path.endswith(".pickle"):
        try:
            obj = pickle.loads(data)
            obj = _extract_trace_obj(obj)
            if isinstance(obj, (list, tuple)):
                out = bytearray(len(obj))
                for i, x in enumerate(obj):
                    out[i] = _to_bool(x)
                return out
        except Exception:
            pass

    text: Optional[str] = None
    try:
        text = data.decode("utf-8", errors="ignore").strip()
    except Exception:
        text = None

    if text:
        if text and (text[0] == "[" or text[0] == "{"):
            try:
                obj = json.loads(text)
                obj = _extract_trace_obj(obj)
                if isinstance(obj, (list, tuple)):
                    out = bytearray(len(obj))
                    for i, x in enumerate(obj):
                        out[i] = _to_bool(x)
                    return out
            except Exception:
                pass

        # Line-based parsing (CSV/TSV/space separated). Use last column as availability.
        lines = text.splitlines()
        vals = bytearray()
        append = vals.append
        for line in lines:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            # Split by comma if present else whitespace.
            if "," in s:
                parts = [p.strip() for p in s.split(",") if p.strip() != ""]
            else:
                parts = s.split()
            if not parts:
                continue
            append(_to_bool(parts[-1]))
        return vals

    return bytearray()


class Solution(MultiRegionStrategy):
    NAME = "trace_aware_multi_region"

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

        self._task_duration_s = _as_scalar(getattr(self, "task_duration", 0.0))
        self._deadline_s = _as_scalar(getattr(self, "deadline", 0.0))
        self._restart_overhead_s = _as_scalar(getattr(self, "restart_overhead", 0.0))

        self._gap_s = float(getattr(self.env, "gap_seconds", 1.0))
        if self._gap_s <= 0:
            self._gap_s = 1.0

        # Conservative thresholds
        self._panic_slack_s = 2.0 * self._gap_s + 2.0 * self._restart_overhead_s
        self._wait_margin_s = self._panic_slack_s + 0.5 * self._gap_s

        denom = self._gap_s * max(1e-9, (_OD_PRICE - _SPOT_PRICE))
        self._min_run_steps_switch_from_od = max(
            1,
            int(math.ceil((2.0 * self._restart_overhead_s * _OD_PRICE) / denom)),
        )
        # A small cap to avoid overly conservative behavior on very small gaps.
        if self._min_run_steps_switch_from_od > 6:
            self._min_run_steps_switch_from_od = 6

        # Waiting thresholds
        if self._gap_s <= 300:
            self._max_wait_steps_current = 1
            self._max_wait_steps_any = 1
        elif self._gap_s <= 900:
            self._max_wait_steps_current = 2
            self._max_wait_steps_any = 2
        else:
            self._max_wait_steps_current = 3
            self._max_wait_steps_any = 3

        self._done_cache = 0.0
        self._done_len = 0

        self._use_traces = False
        self._offset = 0
        self._offset_calibrated = False

        self._num_regions = 0
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 0

        self._total_steps = int(math.ceil(self._deadline_s / self._gap_s)) + 16
        if self._total_steps < 32:
            self._total_steps = 32

        trace_files = config.get("trace_files", None)
        if isinstance(trace_files, list) and trace_files and self._num_regions > 0:
            try:
                self._build_traces(trace_files)
            except Exception:
                self._use_traces = False

        return self

    def _build_traces(self, trace_files: List[str]) -> None:
        n = self._num_regions
        files = trace_files[:n] if len(trace_files) >= n else (trace_files + [trace_files[-1]] * (n - len(trace_files)))
        avail_by_region: List[bytearray] = []
        for p in files:
            if not p or not isinstance(p, str):
                avail_by_region.append(bytearray())
                continue
            if not os.path.exists(p):
                avail_by_region.append(bytearray())
                continue
            tr = _parse_trace_file(p)
            avail_by_region.append(tr)

        expanded_avail: List[bytearray] = []
        runlens: List[array] = []
        next_spot: List[array] = []

        total_steps = self._total_steps
        for r in range(n):
            orig = avail_by_region[r]
            if not orig:
                expanded = bytearray(total_steps)
            else:
                L = len(orig)
                expanded = bytearray(total_steps)
                for i in range(total_steps):
                    expanded[i] = orig[i % L]
            expanded_avail.append(expanded)

            run = array("I", [0]) * total_steps
            nxt = array("I", [0]) * (total_steps + 1)

            # next spot index
            INF = total_steps + 1
            cur = INF
            for i in range(total_steps - 1, -1, -1):
                if expanded[i]:
                    cur = i
                nxt[i] = cur
            nxt[total_steps] = INF

            # run lengths
            for i in range(total_steps - 1, -1, -1):
                if expanded[i]:
                    run[i] = 1 + (run[i + 1] if i + 1 < total_steps else 0)
                else:
                    run[i] = 0

            runlens.append(run)
            next_spot.append(nxt)

        any_spot = bytearray(total_steps)
        for i in range(total_steps):
            v = 0
            for r in range(n):
                if expanded_avail[r][i]:
                    v = 1
                    break
            any_spot[i] = v

        next_any = array("I", [0]) * (total_steps + 1)
        INF = total_steps + 1
        cur = INF
        for i in range(total_steps - 1, -1, -1):
            if any_spot[i]:
                cur = i
            next_any[i] = cur
        next_any[total_steps] = INF

        self._avail = expanded_avail
        self._runlen = runlens
        self._next_spot = next_spot
        self._any_spot = any_spot
        self._next_any = next_any
        self._use_traces = True
        self._offset = 0
        self._offset_calibrated = False

    def _step_index(self) -> int:
        # robust floor for floats
        t = float(getattr(self.env, "elapsed_seconds", 0.0))
        s = int((t / self._gap_s) + 1e-9)
        if s < 0:
            return 0
        if s >= self._total_steps:
            return self._total_steps - 1
        return s

    def _update_done_cache(self) -> None:
        lst = getattr(self, "task_done_time", None)
        if not isinstance(lst, list):
            return
        n = len(lst)
        if n <= self._done_len:
            return
        self._done_cache += float(sum(lst[self._done_len : n]))
        self._done_len = n

    def _idx_with_offset(self, s: int) -> int:
        idx = s + self._offset
        if idx < 0:
            return 0
        if idx >= self._total_steps:
            return self._total_steps - 1
        return idx

    def _maybe_adjust_offset(self, region: int, s: int, has_spot: bool) -> None:
        if not self._use_traces:
            return
        if region < 0 or region >= self._num_regions:
            return
        base = s
        # Try to keep offset stable; only adjust if mismatch.
        pred = bool(self._avail[region][self._idx_with_offset(base)])
        if pred == bool(has_spot):
            if not self._offset_calibrated:
                self._offset_calibrated = True
            return
        # Search nearby offsets
        best = None
        for d in (0, -1, 1, -2, 2, -3, 3):
            off = self._offset + d
            idx = base + off
            if idx < 0:
                idx = 0
            elif idx >= self._total_steps:
                idx = self._total_steps - 1
            if bool(self._avail[region][idx]) == bool(has_spot):
                best = off
                break
        if best is not None:
            self._offset = best
            self._offset_calibrated = True

    def _best_spot_region(self, idx: int) -> Tuple[Optional[int], int]:
        best_r = None
        best_run = 0
        runlens = self._runlen
        avail = self._avail
        n = self._num_regions
        for r in range(n):
            if avail[r][idx]:
                rl = runlens[r][idx]
                if rl > best_run:
                    best_run = rl
                    best_r = r
        return best_r, best_run

    def _query_env_has_spot(self) -> Optional[bool]:
        env = self.env
        for name in ("has_spot", "spot_available", "spot_availability", "current_has_spot"):
            if hasattr(env, name):
                try:
                    return bool(getattr(env, name))
                except Exception:
                    pass
        for m in ("get_has_spot", "get_current_has_spot", "has_spot_now"):
            if hasattr(env, m):
                try:
                    return bool(getattr(env, m)())
                except Exception:
                    pass
        return None

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_cache()

        remaining_work = self._task_duration_s - self._done_cache
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        t = float(getattr(self.env, "elapsed_seconds", 0.0))
        remaining_time = self._deadline_s - t
        if remaining_time <= 0:
            return ClusterType.NONE

        slack = remaining_time - remaining_work

        # Hard deadline guard: if nearly out of slack, lock to on-demand for reliability.
        # Include a small extra buffer for a potential restart.
        if remaining_time <= remaining_work + self._restart_overhead_s + 0.5 * self._gap_s:
            return ClusterType.ON_DEMAND
        if slack <= self._panic_slack_s:
            return ClusterType.ON_DEMAND

        # If we don't have trace knowledge, fall back to myopic behavior.
        if not self._use_traces or self._num_regions <= 0:
            if has_spot:
                # Avoid OD->spot if it's too unstable is not possible without traces.
                return ClusterType.SPOT
            # If we have plenty of slack, wait; else on-demand.
            if slack >= self._wait_margin_s:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        curr_region = int(self.env.get_current_region())
        s = self._step_index()
        self._maybe_adjust_offset(curr_region, s, has_spot)
        idx = self._idx_with_offset(s)

        # If any spot is available in some region now, try to use it.
        if self._any_spot[idx]:
            # Prefer staying if current region has spot now (avoid restarts).
            if 0 <= curr_region < self._num_regions and self._avail[curr_region][idx]:
                # If currently on-demand, only switch to spot if the run is long enough.
                if last_cluster_type == ClusterType.ON_DEMAND:
                    if self._runlen[curr_region][idx] < self._min_run_steps_switch_from_od:
                        return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            best_r, best_run = self._best_spot_region(idx)

            # If current region will regain spot very soon, and we have ample slack, wait to avoid restart overhead.
            if 0 <= curr_region < self._num_regions:
                nxt = self._next_spot[curr_region][idx]
                delay = int(nxt - idx) if nxt <= self._total_steps else 10**9
                if delay <= self._max_wait_steps_current and slack >= (delay * self._gap_s + self._wait_margin_s):
                    return ClusterType.NONE

            if best_r is not None:
                # If currently on-demand, only switch to spot if it's stable enough.
                if last_cluster_type == ClusterType.ON_DEMAND and best_run < self._min_run_steps_switch_from_od:
                    return ClusterType.ON_DEMAND

                if best_r != curr_region:
                    self.env.switch_region(int(best_r))
                    # If env can tell us spot is unavailable after switching, fail safe to on-demand.
                    env_has = self._query_env_has_spot()
                    if env_has is False:
                        return ClusterType.ON_DEMAND
                return ClusterType.SPOT

            # Fallback: should not happen if _any_spot is true.
            return ClusterType.ON_DEMAND

        # No spot anywhere at this step: decide whether to wait or go on-demand.
        nxt_any = self._next_any[idx]
        delay_any = int(nxt_any - idx) if nxt_any <= self._total_steps else 10**9
        if delay_any <= self._max_wait_steps_any and slack >= (delay_any * self._gap_s + self._wait_margin_s):
            return ClusterType.NONE

        return ClusterType.ON_DEMAND
import json
import math
import os
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None", None))


def _to_bool(x: Any) -> Optional[bool]:
    if x is None:
        return None
    if isinstance(x, bool):
        return x
    if isinstance(x, (int, float)):
        return bool(x > 0.5)
    if isinstance(x, str):
        s = x.strip().lower()
        if s in ("1", "true", "t", "yes", "y", "on"):
            return True
        if s in ("0", "false", "f", "no", "n", "off", "", "none", "null", "nan"):
            return False
        try:
            v = float(s)
            return bool(v > 0.5)
        except Exception:
            return None
    return None


def _load_trace_file(path: str) -> List[bool]:
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            txt = f.read().strip()
        if not txt:
            return []
        if txt[0] in "[{":
            data = json.loads(txt)
            if isinstance(data, list):
                out = []
                for v in data:
                    b = _to_bool(v)
                    if b is None:
                        continue
                    out.append(b)
                return out
            if isinstance(data, dict):
                for k in ("availability", "avail", "has_spot", "spot", "trace", "values", "data"):
                    if k in data and isinstance(data[k], list):
                        out = []
                        for v in data[k]:
                            b = _to_bool(v)
                            if b is None:
                                continue
                            out.append(b)
                        if out:
                            return out
                for v in data.values():
                    if isinstance(v, list):
                        out = []
                        for e in v:
                            b = _to_bool(e)
                            if b is None:
                                continue
                            out.append(b)
                        if out:
                            return out
        out = []
        lines = txt.splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line[0] == "#":
                continue
            parts = [p.strip() for p in line.replace("\t", ",").split(",") if p.strip() != ""]
            if not parts:
                continue
            candidates = parts[-2:] if len(parts) >= 2 else parts
            b = None
            for c in reversed(candidates):
                b = _to_bool(c)
                if b is not None:
                    break
            if b is None:
                continue
            out.append(b)
        return out
    except Exception:
        return []


def _downsample_to_expected(raw: Sequence[bool], expected_len: int) -> List[bool]:
    if not raw:
        return []
    n = len(raw)
    if expected_len <= 0:
        return list(raw)
    if n <= expected_len:
        return list(raw)
    if n <= int(expected_len * 1.25):
        return list(raw[:expected_len])
    stride = int(round(n / expected_len))
    if stride <= 1:
        return list(raw[:expected_len])
    ds = list(raw[::stride])
    if len(ds) > expected_len:
        ds = ds[:expected_len]
    return ds


def _precompute_run_and_next(trace: Sequence[bool]) -> Tuple[array, array]:
    n = len(trace)
    run = array("I", [0]) * (n + 1)
    nxt = array("I", [0]) * (n + 1)
    INF = n + 10_000_000
    nxt[n] = INF
    run[n] = 0
    for i in range(n - 1, -1, -1):
        if trace[i]:
            run[i] = run[i + 1] + 1
            nxt[i] = i
        else:
            run[i] = 0
            nxt[i] = nxt[i + 1]
    return run, nxt


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_trace_aware"

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

        self._committed_ondemand = False
        self._work_done = 0.0
        self._last_done_len = 0

        self._use_trace = False
        self._trace_len = 0
        self._trace_avail: List[bytearray] = []
        self._trace_run: List[array] = []
        self._trace_next: List[array] = []
        self._trace_mismatch = 0
        self._trace_checked = 0

        self._finish_buffer = max(600.0, 2.0 * float(self.env.gap_seconds) + 5.0 * float(self.restart_overhead))
        self._overhead_steps_equiv = int(math.ceil(float(self.restart_overhead) / float(self.env.gap_seconds))) if float(self.env.gap_seconds) > 0 else 1

        trace_files = config.get("trace_files", None)
        if isinstance(trace_files, list) and trace_files:
            self._init_traces(trace_files)

        return self

    def _init_traces(self, trace_files: Sequence[str]) -> None:
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = len(trace_files)

        expected_steps = 0
        try:
            expected_steps = int(math.ceil(float(self.deadline) / float(self.env.gap_seconds))) + 1
        except Exception:
            expected_steps = 0

        raw_traces: List[List[bool]] = []
        for i in range(num_regions):
            path = trace_files[i] if i < len(trace_files) else None
            raw = _load_trace_file(path) if path else []
            if expected_steps > 0 and raw:
                raw = _downsample_to_expected(raw, max(expected_steps, min(len(raw), expected_steps * 4)))
            raw_traces.append(raw)

        L = max((len(t) for t in raw_traces), default=0)
        if expected_steps > 0:
            L = max(L, expected_steps)
        if L <= 0:
            self._use_trace = False
            return

        self._trace_len = L
        self._trace_avail = []
        self._trace_run = []
        self._trace_next = []

        for t in raw_traces:
            if len(t) < L:
                t = list(t) + [False] * (L - len(t))
            else:
                t = list(t[:L])
            b = bytearray(1 if x else 0 for x in t)
            self._trace_avail.append(b)
            run, nxt = _precompute_run_and_next([bool(x) for x in b])
            self._trace_run.append(run)
            self._trace_next.append(nxt)

        self._use_trace = True
        self._trace_mismatch = 0
        self._trace_checked = 0

    def _update_work_done(self) -> None:
        td = self.task_done_time
        l = len(td)
        if self._last_done_len < l:
            for i in range(self._last_done_len, l):
                self._work_done += float(td[i])
            self._last_done_len = l

    def _time_index(self) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return 0
        return int(float(self.env.elapsed_seconds) // gap)

    def _trace_has_spot(self, region: int, idx: int) -> bool:
        if not self._use_trace:
            return False
        if region < 0 or region >= len(self._trace_avail):
            return False
        if idx < 0:
            return False
        if idx >= self._trace_len:
            return False
        return bool(self._trace_avail[region][idx])

    def _trace_run_len(self, region: int, idx: int) -> int:
        if not self._use_trace:
            return 0
        if region < 0 or region >= len(self._trace_run):
            return 0
        if idx < 0:
            return 0
        if idx >= self._trace_len:
            return 0
        return int(self._trace_run[region][idx])

    def _trace_next_one(self, region: int, idx: int) -> int:
        if not self._use_trace:
            return 1 << 30
        if region < 0 or region >= len(self._trace_next):
            return 1 << 30
        if idx < 0:
            return 0
        if idx >= self._trace_len:
            return 1 << 30
        return int(self._trace_next[region][idx])

    def _pick_best_region_now(self, idx: int) -> Optional[int]:
        if not self._use_trace:
            return None
        best_r = None
        best_run = -1
        for r in range(len(self._trace_avail)):
            if idx < self._trace_len and self._trace_avail[r][idx]:
                run = int(self._trace_run[r][idx])
                if run > best_run:
                    best_run = run
                    best_r = r
        return best_r

    def _pick_best_region_soon(self, idx: int) -> Optional[int]:
        if not self._use_trace:
            return None
        best_r = None
        best_t = 1 << 30
        for r in range(len(self._trace_avail)):
            t = self._trace_next_one(r, idx)
            if t < best_t:
                best_t = t
                best_r = r
        return best_r

    def _should_force_ondemand(self, last_cluster_type: ClusterType) -> bool:
        remaining_time = float(self.deadline) - float(self.env.elapsed_seconds)
        if remaining_time <= 0:
            return True

        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 0:
            return False

        if self._committed_ondemand:
            return True

        if last_cluster_type == ClusterType.ON_DEMAND:
            startup_overhead = float(self.remaining_restart_overhead)
        else:
            startup_overhead = max(float(self.remaining_restart_overhead), float(self.restart_overhead))

        time_needed = remaining_work + startup_overhead
        return remaining_time <= time_needed + float(self._finish_buffer)

    def _can_switch_now(self) -> bool:
        rr = float(self.remaining_restart_overhead)
        if rr <= 1e-9:
            return True
        return rr >= 0.85 * float(self.restart_overhead)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_work_done()
        remaining_work = float(self.task_duration) - float(self._work_done)
        if remaining_work <= 0:
            return _CT_NONE

        idx = self._time_index()
        cur_region = int(self.env.get_current_region())

        if self._use_trace:
            if 0 <= cur_region < len(self._trace_avail) and 0 <= idx < self._trace_len:
                pred = bool(self._trace_avail[cur_region][idx])
                self._trace_checked += 1
                if pred != bool(has_spot):
                    self._trace_mismatch += 1
                if self._trace_checked >= 200:
                    if (self._trace_mismatch / max(1, self._trace_checked)) > 0.30:
                        self._use_trace = False

        force_ondemand = self._should_force_ondemand(last_cluster_type)
        if force_ondemand:
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        if self._use_trace and self._can_switch_now():
            best_now = self._pick_best_region_now(idx)
            if best_now is not None and best_now != cur_region:
                if has_spot and self._trace_has_spot(best_now, idx):
                    cur_run = self._trace_run_len(cur_region, idx)
                    best_run = self._trace_run_len(best_now, idx)
                    if best_run > cur_run + 2 * self._overhead_steps_equiv:
                        self.env.switch_region(best_now)
                        cur_region = best_now

        if has_spot:
            return ClusterType.SPOT

        if self._use_trace and self._can_switch_now():
            best_soon = self._pick_best_region_soon(idx)
            if best_soon is not None and best_soon != cur_region:
                self.env.switch_region(best_soon)

        return _CT_NONE
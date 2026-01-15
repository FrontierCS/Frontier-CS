import json
import os
import csv
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _scalar(x):
    if isinstance(x, (list, tuple)):
        return x[0] if x else 0.0
    return x


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multiregion_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path) as f:
            config = json.load(f)

        self._spec_dir = os.path.dirname(os.path.abspath(spec_path))
        self._trace_paths = []
        trace_files = config.get("trace_files", []) or []
        for p in trace_files:
            if not isinstance(p, str):
                continue
            if not os.path.isabs(p):
                p = os.path.join(self._spec_dir, p)
            self._trace_paths.append(p)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._done_sum = 0.0
        self._done_len = 0
        self._committed_ondemand = False

        self._trace_ready = False
        self._spot_avail = []
        self._next_on = []
        self._run_len = []
        self._trace_steps = 0

        return self

    @staticmethod
    def _to_bool01(v: Any) -> int:
        if v is None:
            return 0
        if isinstance(v, bool):
            return 1 if v else 0
        if isinstance(v, (int, float)):
            return 1 if v > 0 else 0
        if isinstance(v, str):
            s = v.strip().lower()
            if not s:
                return 0
            if s in ("1", "true", "t", "yes", "y", "spot", "available", "avail", "on"):
                return 1
            if s in ("0", "false", "f", "no", "n", "none", "unavailable", "off"):
                return 0
            try:
                return 1 if float(s) > 0 else 0
            except Exception:
                return 0
        return 0

    @classmethod
    def _extract_series_from_json(cls, obj: Any) -> Optional[List[int]]:
        def convert_list(lst: List[Any]) -> List[int]:
            out = [0] * len(lst)
            for i, x in enumerate(lst):
                out[i] = cls._to_bool01(x)
            return out

        if isinstance(obj, list):
            if not obj:
                return []
            if isinstance(obj[0], dict):
                keys_pref = ("has_spot", "spot", "availability", "available", "avail", "interruptible")
                best_key = None
                for k in keys_pref:
                    if k in obj[0]:
                        best_key = k
                        break
                if best_key is None:
                    for k, v in obj[0].items():
                        if isinstance(v, (bool, int, float, str)):
                            best_key = k
                            break
                if best_key is None:
                    return None
                out = [0] * len(obj)
                for i, d in enumerate(obj):
                    out[i] = cls._to_bool01(d.get(best_key))
                return out
            return convert_list(obj)

        if isinstance(obj, dict):
            keys_pref = ("has_spot", "spot", "availability", "available", "avail", "interruptible", "data", "trace")
            for k in keys_pref:
                v = obj.get(k, None)
                if isinstance(v, list):
                    s = cls._extract_series_from_json(v)
                    if s is not None:
                        return s
            for v in obj.values():
                if isinstance(v, list):
                    s = cls._extract_series_from_json(v)
                    if s is not None:
                        return s
            return None

        return None

    @classmethod
    def _load_trace_file(cls, path: str, limit: Optional[int] = None) -> Optional[bytearray]:
        try:
            with open(path, "r") as f:
                head = f.read(4096)
        except Exception:
            return None

        head_strip = head.lstrip()
        if head_strip.startswith("[") or head_strip.startswith("{"):
            try:
                with open(path, "r") as f:
                    obj = json.load(f)
                series = cls._extract_series_from_json(obj)
                if series is None:
                    return None
                if limit is not None and limit > 0:
                    if len(series) >= limit:
                        series = series[:limit]
                    else:
                        series = series + [0] * (limit - len(series))
                return bytearray(series)
            except Exception:
                pass

        def parse_csv() -> Optional[bytearray]:
            try:
                with open(path, "r", newline="") as f:
                    reader = csv.reader(f)
                    rows = []
                    for row in reader:
                        if not row:
                            continue
                        rows.append(row)
                        if limit is not None and limit > 0 and len(rows) >= limit + 5:
                            # still allow header + few extra; will truncate later
                            pass
                if not rows:
                    return bytearray()
                header = rows[0]
                start_idx = 0
                col_idx = None
                header_lower = [c.strip().lower() for c in header]
                keys_pref = ("has_spot", "spot", "availability", "available", "avail", "interruptible")
                for k in keys_pref:
                    if k in header_lower:
                        col_idx = header_lower.index(k)
                        start_idx = 1
                        break

                out = []
                for row in rows[start_idx:]:
                    if not row:
                        continue
                    if col_idx is not None and col_idx < len(row):
                        out.append(cls._to_bool01(row[col_idx]))
                    else:
                        out.append(cls._to_bool01(row[-1]))
                    if limit is not None and limit > 0 and len(out) >= limit:
                        break
                if limit is not None and limit > 0:
                    if len(out) < limit:
                        out.extend([0] * (limit - len(out)))
                return bytearray(out)
            except Exception:
                return None

        ba = parse_csv()
        if ba is not None:
            return ba

        # Fallback: parse as whitespace/comma-separated tokens.
        try:
            out = []
            with open(path, "r") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    if "," in s:
                        toks = [t for t in s.split(",") if t.strip() != ""]
                    else:
                        toks = s.split()
                    for t in toks:
                        out.append(cls._to_bool01(t))
                        if limit is not None and limit > 0 and len(out) >= limit:
                            break
                    if limit is not None and limit > 0 and len(out) >= limit:
                        break
            if limit is not None and limit > 0 and len(out) < limit:
                out.extend([0] * (limit - len(out)))
            return bytearray(out)
        except Exception:
            return None

    def _ensure_trace_ready(self):
        if self._trace_ready:
            return

        num_regions = 0
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = 0
        if num_regions <= 0:
            self._trace_ready = True
            return

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        deadline_s = float(_scalar(getattr(self, "deadline", 0.0)) or 0.0)
        steps_total = int(deadline_s / gap + 1.000001)
        if steps_total < 1:
            steps_total = 1
        self._trace_steps = steps_total

        self._spot_avail = [bytearray(steps_total) for _ in range(num_regions)]
        self._next_on = []
        self._run_len = []

        paths = self._trace_paths[:num_regions] if self._trace_paths else []
        for r in range(num_regions):
            ba = None
            if r < len(paths):
                ba = self._load_trace_file(paths[r], limit=steps_total)
            if ba is None:
                ba = bytearray(steps_total)
            if len(ba) < steps_total:
                ba.extend(b"\x00" * (steps_total - len(ba)))
            elif len(ba) > steps_total:
                ba = ba[:steps_total]
            self._spot_avail[r] = ba

            n = steps_total
            inf = n + 1
            nxt = array("I", [0]) * (n + 1)
            run = array("I", [0]) * (n + 1)
            nxt[n] = inf
            run[n] = 0
            for t in range(n - 1, -1, -1):
                if ba[t]:
                    nxt[t] = t
                    run[t] = run[t + 1] + 1
                else:
                    nxt[t] = nxt[t + 1]
                    run[t] = 0
            self._next_on.append(nxt)
            self._run_len.append(run)

        self._trace_ready = True

    def _update_done_sum(self):
        td = getattr(self, "task_done_time", None)
        if not isinstance(td, list):
            return
        n = len(td)
        if n <= self._done_len:
            return
        s = 0.0
        for i in range(self._done_len, n):
            try:
                s += float(td[i])
            except Exception:
                continue
        self._done_sum += s
        self._done_len = n

    def _step_index(self) -> int:
        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        t = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        if gap <= 0:
            return int(t)
        return int(t // gap)

    def _maybe_switch_to_best_next_spot_region(self, step_idx: int):
        if not self._trace_ready or not self._next_on:
            return
        if step_idx < 0:
            return
        if step_idx >= self._trace_steps:
            return

        try:
            cur = int(self.env.get_current_region())
        except Exception:
            cur = 0

        n = len(self._next_on)
        best_r = cur
        best_j = self._trace_steps + 1
        best_run = 0

        for r in range(n):
            j = int(self._next_on[r][step_idx])
            if j < best_j:
                best_j = j
                if j <= self._trace_steps:
                    best_run = int(self._run_len[r][j]) if j < len(self._run_len[r]) else 0
                else:
                    best_run = 0
                best_r = r
            elif j == best_j:
                run = int(self._run_len[r][j]) if (j < self._trace_steps and j < len(self._run_len[r])) else 0
                if run > best_run:
                    best_run = run
                    best_r = r

        if best_r != cur:
            try:
                self.env.switch_region(best_r)
            except Exception:
                pass

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_trace_ready()
        self._update_done_sum()

        task_duration = float(_scalar(getattr(self, "task_duration", 0.0)) or 0.0)
        deadline = float(_scalar(getattr(self, "deadline", 0.0)) or 0.0)
        restart_overhead = float(_scalar(getattr(self, "restart_overhead", 0.0)) or 0.0)

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        remaining_time = deadline - elapsed
        remaining_work = task_duration - self._done_sum
        if remaining_work <= 0.0:
            return ClusterType.NONE

        remaining_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)

        gap = float(getattr(self.env, "gap_seconds", 1.0) or 1.0)
        safety_buffer = max(1.0, min(600.0, 0.5 * restart_overhead, 0.1 * gap))

        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead_if_ondemand_now = max(0.0, remaining_overhead)
        else:
            overhead_if_ondemand_now = restart_overhead

        if (not self._committed_ondemand) and (remaining_time <= remaining_work + overhead_if_ondemand_now + safety_buffer):
            self._committed_ondemand = True

        if self._committed_ondemand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        step_idx = self._step_index()
        # Switch only if not mid-overhead (avoid resetting a partially-paid overhead).
        if remaining_overhead <= 1e-9:
            self._maybe_switch_to_best_next_spot_region(step_idx)

        return ClusterType.NONE
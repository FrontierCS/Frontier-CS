import json
import math
from argparse import Namespace
from array import array
from typing import List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _to_bool_token(tok: str) -> Optional[bool]:
    if tok is None:
        return None
    s = tok.strip().strip('"').strip("'")
    if not s:
        return None
    sl = s.lower()
    if sl in ("1", "true", "t", "yes", "y", "on", "up", "available", "avail"):
        return True
    if sl in ("0", "false", "f", "no", "n", "off", "down", "unavailable", "unavail"):
        return False
    try:
        v = float(s)
        return v > 0.0
    except Exception:
        return None


def _load_trace_file(path: str, max_len: int) -> Optional[bytearray]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            head = f.read(4096)
    except Exception:
        try:
            with open(path, "r") as f:
                head = f.read(4096)
        except Exception:
            return None

    head_stripped = head.lstrip()
    if head_stripped.startswith("[") or head_stripped.startswith("{"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            data = None
            if isinstance(obj, list):
                data = obj
            elif isinstance(obj, dict):
                for k in ("availability", "avail", "spot", "has_spot", "available", "trace", "values", "data"):
                    if k in obj and isinstance(obj[k], list):
                        data = obj[k]
                        break
                if data is None:
                    for v in obj.values():
                        if isinstance(v, list):
                            data = v
                            break
            if data is None:
                return None
            out = bytearray()
            for x in data:
                if len(out) >= max_len:
                    break
                if isinstance(x, (int, float)):
                    out.append(1 if float(x) > 0 else 0)
                elif isinstance(x, bool):
                    out.append(1 if x else 0)
                elif isinstance(x, str):
                    b = _to_bool_token(x)
                    if b is None:
                        continue
                    out.append(1 if b else 0)
                elif isinstance(x, dict):
                    val = None
                    for k in ("availability", "avail", "spot", "has_spot", "available", "state"):
                        if k in x:
                            val = x[k]
                            break
                    if val is None:
                        continue
                    if isinstance(val, (int, float)):
                        out.append(1 if float(val) > 0 else 0)
                    elif isinstance(val, bool):
                        out.append(1 if val else 0)
                    elif isinstance(val, str):
                        b = _to_bool_token(val)
                        if b is None:
                            continue
                        out.append(1 if b else 0)
            return out if out else None
        except Exception:
            pass

    try:
        out = bytearray()
        with open(path, "r", encoding="utf-8") as f:
            first = None
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                first = line
                break
            if first is None:
                return None

            delim = None
            if "," in first:
                delim = ","
            elif "\t" in first:
                delim = "\t"

            def split_line(ln: str) -> List[str]:
                if delim is None:
                    return ln.split()
                return ln.split(delim)

            toks = split_line(first)
            has_alpha = any(any(c.isalpha() for c in t) for t in toks)
            col_idx = -1
            if has_alpha:
                header = [t.strip().strip('"').strip("'").lower() for t in toks]
                for i, h in enumerate(header):
                    if any(key in h for key in ("avail", "spot", "available", "state", "interrupt")):
                        col_idx = i
                        break
                if col_idx < 0:
                    col_idx = len(header) - 1
            else:
                val_tok = toks[-1] if toks else ""
                b = _to_bool_token(val_tok)
                if b is not None:
                    out.append(1 if b else 0)

            for line in f:
                if len(out) >= max_len:
                    break
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                toks = split_line(line)
                if not toks:
                    continue
                tok = toks[col_idx] if 0 <= col_idx < len(toks) else toks[-1]
                b = _to_bool_token(tok)
                if b is None:
                    continue
                out.append(1 if b else 0)
        return out if out else None
    except Exception:
        return None


class Solution(MultiRegionStrategy):
    NAME = "greedy_deadline_aware"

    SPOT_PRICE = 0.9701
    ON_DEMAND_PRICE = 3.06

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

        self._trace_files = list(config.get("trace_files", [])) if isinstance(config.get("trace_files", []), list) else []
        self._avail: List[Optional[bytearray]] = []
        self._streak: List[Optional[array]] = []
        self._use_traces = False
        self._traces_valid = True
        self._trace_checks = 0
        self._trace_mismatches = 0

        self._commit_ondemand = False

        self._done_sum = 0.0
        self._done_len = 0

        self._task_duration_sec = float(self.task_duration[0]) if isinstance(self.task_duration, list) else float(self.task_duration)
        self._deadline_sec = float(self.deadline)
        self._restart_overhead_sec = float(self.restart_overhead[0]) if isinstance(self.restart_overhead, list) else float(self.restart_overhead)

        denom = (self.ON_DEMAND_PRICE - self.SPOT_PRICE)
        if denom <= 1e-12:
            self._min_spot_run_seconds = self._restart_overhead_sec
        else:
            self._min_spot_run_seconds = self._restart_overhead_sec * (self.ON_DEMAND_PRICE / denom)

        max_len = int(self._deadline_sec) + 2
        if max_len < 1:
            max_len = 1

        if self._trace_files:
            for p in self._trace_files:
                arr = _load_trace_file(p, max_len=max_len)
                if arr is None:
                    self._avail.append(None)
                    self._streak.append(None)
                    continue
                st = array("I", [0]) * len(arr)
                run = 0
                for i in range(len(arr) - 1, -1, -1):
                    if arr[i]:
                        run += 1
                    else:
                        run = 0
                    st[i] = run
                self._avail.append(arr)
                self._streak.append(st)
            self._use_traces = any(a is not None for a in self._avail)

        return self

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        if td is None:
            return
        n = len(td)
        if n <= self._done_len:
            return
        add = 0.0
        for i in range(self._done_len, n):
            add += float(td[i])
        self._done_sum += add
        self._done_len = n

    def _step_index(self) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return 0
        return int(round(float(self.env.elapsed_seconds) / gap))

    def _best_spot_region(self, idx: int, num_regions: int) -> Tuple[int, int]:
        best_r = -1
        best_s = 0
        for r in range(num_regions):
            a = self._avail[r] if r < len(self._avail) else None
            s = self._streak[r] if r < len(self._streak) else None
            if a is None or s is None:
                continue
            if idx < 0 or idx >= len(a):
                continue
            if a[idx]:
                st = int(s[idx])
                if st > best_s:
                    best_s = st
                    best_r = r
        return best_r, best_s

    def _current_trace_has_spot(self, region: int, idx: int) -> Optional[bool]:
        if region < 0 or region >= len(self._avail):
            return None
        a = self._avail[region]
        if a is None:
            return None
        if idx < 0 or idx >= len(a):
            return None
        return bool(a[idx])

    def _required_steps_ondemand(self, remaining_work: float, gap: float, last_cluster_type: ClusterType) -> int:
        overhead = self._restart_overhead_sec
        if last_cluster_type == ClusterType.ON_DEMAND:
            try:
                overhead = float(self.remaining_restart_overhead)
            except Exception:
                overhead = self._restart_overhead_sec
            if overhead < 0:
                overhead = 0.0
        total = overhead + remaining_work
        if total <= 0:
            return 0
        return int(math.ceil(total / gap - 1e-12))

    def _required_steps_ondemand_if_wait_one(self, remaining_work: float, gap: float) -> int:
        total = self._restart_overhead_sec + remaining_work
        if total <= 0:
            return 0
        return int(math.ceil(total / gap - 1e-12))

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_sum()

        remaining_work = self._task_duration_sec - self._done_sum
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        gap = float(self.env.gap_seconds)
        if gap <= 0:
            return ClusterType.ON_DEMAND

        remaining_time = self._deadline_sec - float(self.env.elapsed_seconds)
        steps_left = int(math.floor((remaining_time + 1e-9) / gap))
        if steps_left <= 0:
            return ClusterType.ON_DEMAND

        if self._commit_ondemand:
            return ClusterType.ON_DEMAND

        required_now = self._required_steps_ondemand(remaining_work, gap, last_cluster_type)
        if required_now >= steps_left:
            self._commit_ondemand = True
            return ClusterType.ON_DEMAND

        required_if_wait = self._required_steps_ondemand_if_wait_one(remaining_work, gap)
        safe_wait_one = required_if_wait <= (steps_left - 1)

        cur_region = int(self.env.get_current_region())

        if self._use_traces and self._traces_valid:
            idx = self._step_index()
            tr = self._current_trace_has_spot(cur_region, idx)
            if tr is not None:
                self._trace_checks += 1
                if bool(tr) != bool(has_spot):
                    self._trace_mismatches += 1
                if self._trace_checks >= 50 and self._trace_mismatches > 10:
                    self._traces_valid = False

        if last_cluster_type == ClusterType.SPOT and has_spot:
            return ClusterType.SPOT

        if not (self._use_traces and self._traces_valid):
            if has_spot:
                return ClusterType.SPOT
            if safe_wait_one:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        num_regions = int(self.env.get_num_regions())
        if num_regions <= 0:
            num_regions = len(self._avail)
        else:
            num_regions = min(num_regions, len(self._avail))

        idx = self._step_index()
        best_r, best_streak_steps = self._best_spot_region(idx, num_regions)

        if best_r < 0 or best_streak_steps <= 0:
            if safe_wait_one:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        best_streak_seconds = best_streak_steps * gap

        if best_streak_seconds < self._min_spot_run_seconds:
            if safe_wait_one:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        if best_r != cur_region:
            self.env.switch_region(best_r)

        return ClusterType.SPOT

import json
import math
import gzip
import os
import re
from argparse import Namespace
from array import array
from typing import Any, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cbl_multi_region_v1"

    def solve(self, spec_path: str) -> "Solution":
        with open(spec_path, "r") as f:
            config = json.load(f)

        args = Namespace(
            deadline_hours=float(config["deadline"]),
            task_duration_hours=[float(config["duration"])],
            restart_overhead_hours=[float(config["overhead"])],
            inter_task_overhead=[0.0],
        )
        super().__init__(args)

        self._trace_paths: List[str] = list(config.get("trace_files", []))
        self._avail: List[bytearray] = []
        self._next_true: List[array] = []
        self._run_len: List[array] = []
        self._max_len: int = 0

        for p in self._trace_paths:
            try:
                a = self._load_trace(p)
            except Exception:
                a = bytearray()
            self._avail.append(a)
            self._max_len = max(self._max_len, len(a))

        for a in self._avail:
            nxt, run = self._precompute_next_and_run(a)
            self._next_true.append(nxt)
            self._run_len.append(run)

        self._done_work: float = 0.0
        self._done_len: int = 0
        self._locked_on_demand: bool = False

        return self

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._update_done_work()
        if self._done_work >= self.task_duration - 1e-9:
            return ClusterType.NONE

        gap = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        time_left = self.deadline - elapsed
        remaining_work = self.task_duration - self._done_work
        slack = time_left - remaining_work

        # Conservative lock to ensure completion.
        # Once locked, never switch away from on-demand.
        # Use a margin that covers a few restarts and discretization.
        safety_margin = 6.0 * self.restart_overhead + 4.0 * gap
        if not self._locked_on_demand and time_left <= remaining_work + safety_margin:
            self._locked_on_demand = True

        if self._locked_on_demand:
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        # Spot not available (as indicated by environment). Consider pausing if slack allows.
        idx = self._time_index(elapsed, gap)
        next_any_idx, best_region = self._best_future_region(idx)

        if next_any_idx is None or best_region is None:
            return ClusterType.ON_DEMAND

        wait_steps = max(0, next_any_idx - idx)
        wait_time = wait_steps * gap

        # Estimate overhead impact conservatively; if we pause, we'll almost surely incur at least one overhead.
        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        overhead_est = max(pending_overhead, self.restart_overhead)

        # If we can afford waiting for spot, pause (no cost) and switch region to be ready.
        pause_margin = wait_time + overhead_est + 3.0 * gap + 2.0 * self.restart_overhead
        if slack > pause_margin:
            try:
                cur = int(self.env.get_current_region())
            except Exception:
                cur = 0
            if best_region != cur:
                try:
                    self.env.switch_region(int(best_region))
                except Exception:
                    pass
            return ClusterType.NONE

        return ClusterType.ON_DEMAND

    def _update_done_work(self) -> None:
        td = getattr(self, "task_done_time", None)
        if not td:
            return
        n = len(td)
        if n <= self._done_len:
            return
        self._done_work += float(sum(td[self._done_len : n]))
        self._done_len = n

    @staticmethod
    def _time_index(elapsed_seconds: float, gap_seconds: float) -> int:
        if gap_seconds <= 0:
            return 0
        # Use floor with small epsilon for floating stability.
        return int((elapsed_seconds + 1e-9) // gap_seconds)

    def _best_future_region(self, idx: int) -> Tuple[Optional[int], Optional[int]]:
        num_regions = 0
        try:
            num_regions = int(self.env.get_num_regions())
        except Exception:
            num_regions = len(self._avail)

        if num_regions <= 0:
            return None, None

        limit = min(num_regions, len(self._avail), len(self._next_true))
        if limit <= 0:
            return None, None

        best_region: Optional[int] = None
        best_next: Optional[int] = None
        best_run: int = -1

        for r in range(limit):
            nxt_arr = self._next_true[r]
            run_arr = self._run_len[r]
            a_len = len(self._avail[r])

            if idx < 0:
                nxt = 0
            elif idx >= len(nxt_arr):
                nxt = a_len
            else:
                nxt = int(nxt_arr[idx])

            if best_next is None or nxt < best_next:
                best_next = nxt
                best_region = r
                best_run = self._run_at(run_arr, nxt)
            elif nxt == best_next:
                run = self._run_at(run_arr, nxt)
                if run > best_run:
                    best_run = run
                    best_region = r

        if best_next is None or best_next >= 10**9:
            return None, None
        if best_next is not None and best_region is not None:
            # If nxt equals the trace length, it means no future availability in that trace.
            # Treat as no availability.
            a_len = len(self._avail[best_region]) if best_region < len(self._avail) else 0
            if a_len == 0 or best_next >= a_len:
                return None, None
        return best_next, best_region

    @staticmethod
    def _run_at(run_arr: array, idx: int) -> int:
        if idx < 0:
            return 0
        if idx >= len(run_arr):
            return 0
        return int(run_arr[idx])

    @staticmethod
    def _precompute_next_and_run(avail: bytearray) -> Tuple[array, array]:
        n = len(avail)
        nxt = array("I", [0]) * (n + 1)
        run = array("I", [0]) * (n + 1)

        next_true = n
        runlen = 0
        nxt[n] = n
        run[n] = 0

        for i in range(n - 1, -1, -1):
            if avail[i]:
                next_true = i
                runlen += 1
            else:
                runlen = 0
            nxt[i] = next_true
            run[i] = runlen

        return nxt, run

    @staticmethod
    def _open_maybe_gzip(path: str):
        if path.endswith(".gz"):
            return gzip.open(path, "rt", encoding="utf-8", errors="ignore")
        return open(path, "rt", encoding="utf-8", errors="ignore")

    @classmethod
    def _load_trace(cls, path: str) -> bytearray:
        if not path or not os.path.exists(path):
            return bytearray()

        with cls._open_maybe_gzip(path) as f:
            data = f.read()

        s = data.strip()
        if not s:
            return bytearray()

        # Try JSON formats
        if s[0] in "[{":
            try:
                obj = json.loads(s)
                seq = cls._extract_sequence_from_json(obj)
                if seq is not None:
                    return cls._to_avail_bytearray(seq)
            except Exception:
                pass

        # Fallback: parse tokens from text
        tokens = re.split(r"[,\s]+", s)
        out = bytearray()
        for tok in tokens:
            if not tok:
                continue
            v = cls._token_to_bool(tok)
            if v is None:
                continue
            out.append(1 if v else 0)
        return out

    @staticmethod
    def _extract_sequence_from_json(obj: Any) -> Optional[List[Any]]:
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            for k in ("availability", "avail", "has_spot", "spot", "trace", "data", "values"):
                if k in obj and isinstance(obj[k], list):
                    return obj[k]
            # Common nested structure: {"data": {"availability": [...]}}
            for v in obj.values():
                if isinstance(v, dict):
                    for k in ("availability", "avail", "has_spot", "spot", "trace", "data", "values"):
                        if k in v and isinstance(v[k], list):
                            return v[k]
                if isinstance(v, list):
                    return v
        return None

    @staticmethod
    def _to_avail_bytearray(seq: List[Any]) -> bytearray:
        out = bytearray()
        for x in seq:
            if isinstance(x, bool):
                out.append(1 if x else 0)
            elif isinstance(x, (int, float)):
                out.append(1 if float(x) > 0.0 else 0)
            elif isinstance(x, str):
                b = Solution._token_to_bool(x)
                if b is None:
                    continue
                out.append(1 if b else 0)
            else:
                # Unknown element type; skip
                continue
        return out

    @staticmethod
    def _token_to_bool(tok: str) -> Optional[bool]:
        t = tok.strip().lower()
        if not t:
            return None
        if t in ("1", "true", "t", "yes", "y", "on"):
            return True
        if t in ("0", "false", "f", "no", "n", "off"):
            return False
        try:
            v = float(t)
            return v > 0.0
        except Exception:
            return None

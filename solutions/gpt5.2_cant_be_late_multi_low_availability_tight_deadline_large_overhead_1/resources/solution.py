import json
from argparse import Namespace
from array import array
from typing import Any, Dict, List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_trace_aware_v1"

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

        self._trace_files: List[str] = list(config.get("trace_files", [])) if isinstance(config, dict) else []
        self._raw_traces: Optional[List[List[int]]] = None
        self._trace_load_failed: bool = False

        self._traces: Optional[List[bytearray]] = None
        self._run_len: Optional[List[array]] = None
        self._next_true: Optional[List[array]] = None
        self._trace_len: int = 0
        self._trace_ready: bool = False

        self._gap_cached: Optional[float] = None
        self._num_regions_cached: Optional[int] = None

        self._done_len_cached: int = 0
        self._work_done_cached: float = 0.0

        self._consecutive_wait: int = 0
        self._rr_region: int = 0

        if self._trace_files:
            try:
                self._raw_traces = [self._read_trace_file(p) for p in self._trace_files]
            except Exception:
                self._raw_traces = None
                self._trace_load_failed = True

        return self

    def _read_trace_file(self, path: str) -> List[int]:
        with open(path, "r") as f:
            first = f.read(1)
            f.seek(0)
            if first in "[{":
                obj = json.load(f)
                vals = self._extract_trace_values(obj)
                return self._coerce_to_01(vals)

            out: List[int] = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                line = line.replace(",", " ").replace("\t", " ")
                for tok in line.split():
                    try:
                        v = float(tok)
                    except Exception:
                        continue
                    out.append(1 if v > 0.0 else 0)
            return out

    def _extract_trace_values(self, obj: Any) -> Any:
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            for k in ("availability", "avail", "spot", "data", "values", "trace", "traces"):
                if k in obj and isinstance(obj[k], list):
                    return obj[k]
            for v in obj.values():
                if isinstance(v, list):
                    return v
        return []

    def _coerce_to_01(self, vals: Any) -> List[int]:
        if not isinstance(vals, list):
            return []
        out: List[int] = []
        for x in vals:
            if isinstance(x, bool):
                out.append(1 if x else 0)
            elif isinstance(x, (int, float)):
                out.append(1 if float(x) > 0.0 else 0)
            elif isinstance(x, str):
                s = x.strip().lower()
                if s in ("1", "true", "t", "yes", "y", "on"):
                    out.append(1)
                elif s in ("0", "false", "f", "no", "n", "off"):
                    out.append(0)
                else:
                    try:
                        out.append(1 if float(s) > 0.0 else 0)
                    except Exception:
                        continue
            else:
                continue
        return out

    def _lazy_init_traces(self) -> None:
        if self._trace_ready or self._trace_load_failed:
            return
        if self._raw_traces is None:
            self._trace_ready = False
            return
        if self._num_regions_cached is None:
            try:
                self._num_regions_cached = int(self.env.get_num_regions())
            except Exception:
                self._num_regions_cached = None
                self._trace_ready = False
                return
        if self._num_regions_cached is None:
            self._trace_ready = False
            return
        if len(self._raw_traces) < self._num_regions_cached:
            self._trace_ready = False
            return

        traces_raw = self._raw_traces[: self._num_regions_cached]
        max_len = 0
        for t in traces_raw:
            if len(t) > max_len:
                max_len = len(t)
        if max_len <= 0:
            self._trace_ready = False
            return

        traces: List[bytearray] = []
        run_len: List[array] = []
        next_true: List[array] = []
        for t in traces_raw:
            if not t:
                b = bytearray(max_len)
            else:
                last = t[-1]
                if len(t) < max_len:
                    t2 = t + [last] * (max_len - len(t))
                else:
                    t2 = t[:max_len]
                b = bytearray(t2)
            traces.append(b)

        for r in range(len(traces)):
            a = traces[r]
            L = len(a)
            rl = array("I", [0]) * L
            nt = array("I", [0]) * L
            next_idx = L
            consec = 0
            for i in range(L - 1, -1, -1):
                if a[i]:
                    consec += 1
                    rl[i] = consec
                    next_idx = i
                    nt[i] = i
                else:
                    consec = 0
                    rl[i] = 0
                    nt[i] = next_idx
            run_len.append(rl)
            next_true.append(nt)

        self._traces = traces
        self._run_len = run_len
        self._next_true = next_true
        self._trace_len = max_len
        self._trace_ready = True

    def _update_work_done_cache(self) -> float:
        td = self.task_done_time
        n = len(td)
        if n == self._done_len_cached:
            return self._work_done_cached
        s = self._work_done_cached
        for i in range(self._done_len_cached, n):
            try:
                s += float(td[i])
            except Exception:
                pass
        self._done_len_cached = n
        self._work_done_cached = s
        return s

    def _get_step_index(self) -> int:
        gap = float(self.env.gap_seconds)
        if gap <= 0.0:
            return 0
        return int(float(self.env.elapsed_seconds) // gap)

    def _choose_region_for_next_step(self, next_idx: int) -> Optional[int]:
        if self._num_regions_cached is None:
            try:
                self._num_regions_cached = int(self.env.get_num_regions())
            except Exception:
                return None
        nreg = self._num_regions_cached
        if nreg is None or nreg <= 0:
            return None

        if self._trace_ready and self._traces is not None and self._run_len is not None and self._next_true is not None:
            L = self._trace_len
            if L <= 0:
                return None
            if next_idx < 0:
                next_idx = 0
            if next_idx >= L:
                next_idx = L - 1

            best_r = None
            best_run = -1
            for r in range(nreg):
                if self._traces[r][next_idx]:
                    runv = int(self._run_len[r][next_idx])
                    if runv > best_run:
                        best_run = runv
                        best_r = r
            if best_r is not None:
                return best_r

            best_r = 0
            best_wait = 1 << 30
            for r in range(nreg):
                nt = int(self._next_true[r][next_idx])
                wait = (nt - next_idx) if nt < (1 << 30) else (1 << 29)
                if wait < best_wait:
                    best_wait = wait
                    best_r = r
            return best_r

        # Fallback: round-robin
        self._rr_region = (self._rr_region + 1) % nreg
        return self._rr_region

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        if self._gap_cached is None:
            try:
                self._gap_cached = float(self.env.gap_seconds)
            except Exception:
                self._gap_cached = 0.0
        if self._num_regions_cached is None:
            try:
                self._num_regions_cached = int(self.env.get_num_regions())
            except Exception:
                self._num_regions_cached = None

        self._lazy_init_traces()

        work_done = self._update_work_done_cache()
        remaining_work = float(self.task_duration) - float(work_done)
        if remaining_work <= 0.0:
            self._consecutive_wait = 0
            return ClusterType.NONE

        elapsed = float(self.env.elapsed_seconds)
        time_left = float(self.deadline) - elapsed

        gap = float(self._gap_cached or 0.0)
        overhead = float(self.restart_overhead)
        if gap <= 0.0:
            gap = 1.0

        slack = time_left - remaining_work

        # If already in restart overhead, avoid changing decisions unless forced.
        try:
            pending_overhead = float(self.remaining_restart_overhead)
        except Exception:
            pending_overhead = 0.0

        tight_reserve = 2.0 * gap + 4.0 * overhead
        wait_slack_min = 4.0 * gap + 6.0 * overhead

        # Must finish mode: commit to on-demand when tight.
        if slack <= tight_reserve:
            self._consecutive_wait = 0
            return ClusterType.ON_DEMAND

        # Consume overhead without changing unless spot is forbidden.
        if pending_overhead > 0.0 and last_cluster_type != ClusterType.NONE:
            self._consecutive_wait = 0
            if last_cluster_type == ClusterType.SPOT and not has_spot:
                return ClusterType.ON_DEMAND
            return last_cluster_type

        # Normal decision.
        decision: ClusterType
        if has_spot:
            decision = ClusterType.SPOT
            self._consecutive_wait = 0
            return decision

        # No spot in current region this step.
        t_idx = self._get_step_index()
        next_idx = t_idx + 1

        # Only wait if we expect spot to be available somewhere next step and we have plenty of slack.
        want_wait = False
        if self._trace_ready and self._traces is not None:
            L = self._trace_len
            if L > 0:
                ni = next_idx
                if ni >= L:
                    ni = L - 1
                any_spot_next = False
                nreg = self._num_regions_cached or 0
                for r in range(nreg):
                    if self._traces[r][ni]:
                        any_spot_next = True
                        break
                if any_spot_next and slack >= wait_slack_min and self._consecutive_wait < 1:
                    want_wait = True

        if want_wait:
            # Switch to a good region for next step spot while waiting, but avoid switching if continuing on-demand.
            try:
                current_region = int(self.env.get_current_region())
            except Exception:
                current_region = 0
            target = self._choose_region_for_next_step(next_idx)
            if target is not None and target != current_region:
                try:
                    self.env.switch_region(int(target))
                except Exception:
                    pass
            self._consecutive_wait += 1
            return ClusterType.NONE

        self._consecutive_wait = 0

        # If we are not tight but spot isn't available, run on-demand to keep progress.
        # While doing so, avoid region switching if we are continuing on-demand uninterrupted.
        return ClusterType.ON_DEMAND

import json
import os
from argparse import Namespace
from io import BytesIO
from typing import Callable, List, Optional, Sequence, Tuple

try:
    import numpy as np  # type: ignore
except Exception:
    np = None

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


_CT_SPOT = getattr(ClusterType, "SPOT")
_CT_OD = getattr(ClusterType, "ON_DEMAND")
_CT_NONE = getattr(ClusterType, "NONE", getattr(ClusterType, "None"))


def _to_bool_list(x) -> Optional[List[bool]]:
    if x is None:
        return None
    if isinstance(x, list):
        if not x:
            return []
        if isinstance(x[0], bool):
            return [bool(v) for v in x]
        if isinstance(x[0], (int, float)):
            return [bool(v) for v in x]
        if isinstance(x[0], list) and x[0] and isinstance(x[0][0], (int, float, bool)):
            # If nested, pick last column
            return [bool(row[-1]) for row in x if row]
    return None


def _load_trace_file(path: str) -> Optional[List[bool]]:
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return None

    if not data:
        return []

    # NPY
    if data.startswith(b"\x93NUMPY") and np is not None:
        try:
            arr = np.load(BytesIO(data), allow_pickle=False)
            if hasattr(arr, "tolist"):
                lst = arr.tolist()
                if isinstance(lst, list):
                    if lst and isinstance(lst[0], list):
                        # attempt last column
                        lst2 = [row[-1] for row in lst if row]
                        bl = _to_bool_list(lst2)
                        if bl is not None:
                            return bl
                    bl = _to_bool_list(lst)
                    if bl is not None:
                        return bl
        except Exception:
            pass

    # JSON
    try:
        txt = data.decode("utf-8", errors="ignore").strip()
    except Exception:
        txt = ""

    if txt:
        first = txt[:1]
        if first in "[{":
            try:
                obj = json.loads(txt)
                if isinstance(obj, dict):
                    for k in ("spot", "availability", "avail", "trace", "values", "data"):
                        if k in obj:
                            bl = _to_bool_list(obj[k])
                            if bl is not None:
                                return bl
                    # If dict of regions, not expected here
                    return None
                bl = _to_bool_list(obj)
                if bl is not None:
                    return bl
            except Exception:
                pass

        # Line-based / CSV-ish
        lines = txt.splitlines()
        if lines:
            out: List[bool] = []
            for line in lines:
                s = line.strip()
                if not s:
                    continue
                # ignore comments/headers
                if any(c.isalpha() for c in s[:12]) and ("," in s or "\t" in s or " " in s):
                    # likely header; skip
                    if len(out) == 0:
                        continue
                # split on comma / whitespace
                if "," in s:
                    parts = [p for p in s.split(",") if p.strip() != ""]
                else:
                    parts = s.split()
                if not parts:
                    continue
                token = parts[-1].strip()
                try:
                    v = float(token)
                    out.append(v >= 0.5)
                except Exception:
                    tl = token.lower()
                    if tl in ("true", "t", "yes", "y", "on", "spot", "available", "1"):
                        out.append(True)
                    elif tl in ("false", "f", "no", "n", "off", "unavailable", "0"):
                        out.append(False)
                    else:
                        # If still unknown, skip
                        continue
            if out:
                return out

    return None


class Solution(MultiRegionStrategy):
    NAME = "trace_aware_min_cost"

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

        self._inited = False
        self._od_locked = False

        self._done_work = 0.0
        self._done_len = 0

        self._num_regions = None

        self._trace: Optional[List[List[bool]]] = None
        self._run_len: Optional[List[List[int]]] = None
        self._trace_ready = False

        self._idx_offsets: Optional[Tuple[float, ...]] = None
        self._idx_score: Optional[List[int]] = None
        self._idx_total = 0
        self._idx_chosen_offset = 0.0
        self._idx_calibrated = False
        self._idx_disabled = False

        self._last_action = _CT_NONE
        self._prev_overhead = 0.0
        self._overhead_none_counts_down = False
        self._overhead_none_tested = False
        self._overhead_none_testing = False

        trace_files = config.get("trace_files")
        if isinstance(trace_files, list) and trace_files:
            traces: List[List[bool]] = []
            for p in trace_files:
                if not isinstance(p, str):
                    traces = []
                    break
                # allow relative paths with spec directory
                if not os.path.isabs(p):
                    p2 = os.path.join(os.path.dirname(spec_path), p)
                else:
                    p2 = p
                t = _load_trace_file(p2)
                if t is None:
                    traces = []
                    break
                traces.append(t)
            if traces:
                min_len = min(len(t) for t in traces)
                if min_len > 0:
                    # truncate to common length
                    traces = [t[:min_len] for t in traces]
                    self._trace = traces
                    self._prepare_run_lengths()
        return self

    def _prepare_run_lengths(self) -> None:
        if not self._trace:
            return
        runlens: List[List[int]] = []
        for t in self._trace:
            n = len(t)
            rl = [0] * (n + 1)
            for i in range(n - 1, -1, -1):
                rl[i] = rl[i + 1] + 1 if t[i] else 0
            runlens.append(rl)
        self._run_len = runlens
        self._trace_ready = True

    def _lazy_init(self) -> None:
        if self._inited:
            return
        self._inited = True
        try:
            self._num_regions = int(self.env.get_num_regions())
        except Exception:
            self._num_regions = 1

        if self._trace_ready and self._trace:
            # Calibration offsets in [0, gap) seconds
            g = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
            if g > 0:
                eps = min(1e-6 * g, 1e-3)
                self._idx_offsets = (0.0, 0.5 * g, g - eps)
                self._idx_score = [0, 0, 0]
            else:
                self._idx_disabled = True

    def _update_done_work(self) -> None:
        td = self.task_done_time
        L = len(td)
        i = self._done_len
        if i < L:
            s = 0.0
            while i < L:
                s += float(td[i])
                i += 1
            self._done_work += s
            self._done_len = L

    def _time_index(self, has_spot_param: bool) -> Optional[int]:
        if self._idx_disabled or not self._trace_ready or not self._trace or not self._idx_offsets or not self._idx_score:
            return None
        g = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        if g <= 0:
            self._idx_disabled = True
            return None

        t = float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0)
        cur = 0
        try:
            cur = int(self.env.get_current_region())
        except Exception:
            cur = 0

        # Calibrate offsets against observed has_spot for current region.
        if not self._idx_calibrated and self._idx_total < 80:
            best_possible = True
            for k, off in enumerate(self._idx_offsets):
                idx = int((t + off) // g)
                ok = False
                if 0 <= cur < len(self._trace) and 0 <= idx < len(self._trace[cur]):
                    ok = bool(self._trace[cur][idx]) == bool(has_spot_param)
                else:
                    ok = (False == bool(has_spot_param))
                if ok:
                    self._idx_score[k] += 1
            self._idx_total += 1
            if self._idx_total >= 30:
                best_k = 0
                best_v = self._idx_score[0]
                for k in range(1, len(self._idx_score)):
                    if self._idx_score[k] > best_v:
                        best_v = self._idx_score[k]
                        best_k = k
                if best_v >= int(0.85 * self._idx_total):
                    self._idx_chosen_offset = self._idx_offsets[best_k]
                    self._idx_calibrated = True
                elif self._idx_total >= 80:
                    # Couldn't calibrate reliably; disable traces to avoid errors.
                    self._idx_disabled = True
                    return None

        off = self._idx_chosen_offset if self._idx_calibrated else self._idx_offsets[0]
        idx = int((t + off) // g)
        return idx

    def _spot_anywhere_and_best_region(self, idx: int) -> Tuple[bool, Optional[int]]:
        if not self._trace or not self._run_len:
            return False, None
        n_regions = min(len(self._trace), self._num_regions or len(self._trace))
        best_r = None
        best_len = -1

        cur = 0
        try:
            cur = int(self.env.get_current_region())
        except Exception:
            cur = 0

        # Prefer current region if available to avoid region-switch overhead.
        if 0 <= cur < n_regions:
            tcur = self._trace[cur]
            if 0 <= idx < len(tcur) and tcur[idx]:
                return True, cur

        for r in range(n_regions):
            tr = self._trace[r]
            if idx < 0 or idx >= len(tr):
                continue
            if not tr[idx]:
                continue
            rl = self._run_len[r][idx]
            if rl > best_len:
                best_len = rl
                best_r = r
        return (best_r is not None), best_r

    def _need_on_demand(self, remaining_work: float, time_left: float) -> bool:
        g = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        safety = float(self.restart_overhead) + 2.0 * g
        return time_left <= remaining_work + safety

    def _should_wait_out_overhead(self, remaining_work: float, time_left: float) -> bool:
        if self.remaining_restart_overhead <= 1e-9:
            return False
        if self._od_locked:
            return False
        g = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        safety = float(self.restart_overhead) + 2.0 * g
        slack = time_left - remaining_work
        # Only if enough slack to wait and we believe overhead counts down during NONE.
        if self._overhead_none_counts_down and slack >= self.remaining_restart_overhead + safety:
            return True
        # One-time test when slack is generous.
        if (not self._overhead_none_tested) and (not self._overhead_none_testing) and slack >= 4.0 * safety:
            self._overhead_none_testing = True
            return True
        return False

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_done_work()

        # Detect whether overhead counts down during NONE by observing after a NONE action.
        cur_overhead = float(self.remaining_restart_overhead)
        if self._last_action == _CT_NONE and self._overhead_none_testing:
            if cur_overhead < self._prev_overhead - 1e-9:
                self._overhead_none_counts_down = True
            self._overhead_none_tested = True
            self._overhead_none_testing = False
        self._prev_overhead = cur_overhead

        if self._done_work >= float(self.task_duration) - 1e-6:
            self._last_action = _CT_NONE
            return _CT_NONE

        remaining_work = max(0.0, float(self.task_duration) - self._done_work)
        time_left = max(0.0, float(self.deadline) - float(getattr(self.env, "elapsed_seconds", 0.0) or 0.0))

        if self._od_locked:
            self._last_action = _CT_OD
            return _CT_OD

        if self._need_on_demand(remaining_work, time_left):
            self._od_locked = True
            self._last_action = _CT_OD
            return _CT_OD

        if self._should_wait_out_overhead(remaining_work, time_left):
            self._last_action = _CT_NONE
            return _CT_NONE

        # Trace-aware region selection if available and calibrated; otherwise fallback.
        idx = self._time_index(has_spot)
        if idx is not None and self._trace_ready and (not self._idx_disabled) and self._trace and self._run_len:
            any_spot, best_region = self._spot_anywhere_and_best_region(idx)
            if any_spot and best_region is not None:
                try:
                    cur = int(self.env.get_current_region())
                except Exception:
                    cur = best_region
                if best_region != cur:
                    try:
                        self.env.switch_region(best_region)
                    except Exception:
                        pass
                self._last_action = _CT_SPOT
                return _CT_SPOT

            # No spot anywhere at this time.
            g = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
            safety = float(self.restart_overhead) + 2.0 * g
            slack = time_left - remaining_work
            if slack > safety:
                self._last_action = _CT_NONE
                return _CT_NONE
            self._od_locked = True
            self._last_action = _CT_OD
            return _CT_OD

        # Fallback without traces: use given has_spot in current region only.
        if has_spot:
            self._last_action = _CT_SPOT
            return _CT_SPOT

        # No spot in current region (unknown elsewhere); pause if safe, else on-demand.
        g = float(getattr(self.env, "gap_seconds", 0.0) or 0.0)
        safety = float(self.restart_overhead) + 2.0 * g
        slack = time_left - remaining_work
        if slack > safety:
            self._last_action = _CT_NONE
            return _CT_NONE

        self._od_locked = True
        self._last_action = _CT_OD
        return _CT_OD
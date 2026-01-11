import json
from argparse import Namespace
from array import array
from typing import List, Optional, Sequence, Any

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


def _truthy(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    s = str(v).strip().lower()
    if not s:
        return False
    if s in ("0", "0.0", "false", "f", "no", "n", "none", "null", "nan"):
        return False
    return True


def _extract_list_from_json(obj: Any) -> List[Any]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        for k in ("availability", "avail", "spot", "trace", "data", "values"):
            if k in obj and isinstance(obj[k], list):
                return obj[k]
        for v in obj.values():
            if isinstance(v, list):
                return v
    return []


def _load_trace_file(path: str) -> bytearray:
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except Exception:
        return bytearray()

    if not raw:
        return bytearray()

    s = raw.lstrip()
    if s[:1] in (b"[", b"{"):
        try:
            obj = json.loads(raw.decode("utf-8"))
            lst = _extract_list_from_json(obj)
            ba = bytearray(len(lst))
            for i, v in enumerate(lst):
                ba[i] = 1 if _truthy(v) else 0
            return ba
        except Exception:
            pass

    try:
        text = raw.decode("utf-8", "ignore")
    except Exception:
        return bytearray()

    # Common formats: "0/1 per line", "comma-separated", or "timestamp,0/1" (we take last token).
    tokens = text.replace(",", " ").split()
    if not tokens:
        return bytearray()

    # If tokens look like timestamp,value pairs, try extracting the last column per line
    # by checking if there are many non-binary tokens.
    ba = bytearray()
    non_binary = 0
    for t in tokens[: min(2000, len(tokens))]:
        tl = t.strip().lower()
        if tl in ("0", "1", "true", "false", "t", "f"):
            continue
        try:
            float(tl)
            # numeric but could be timestamp
            if tl not in ("0", "1", "0.0", "1.0"):
                non_binary += 1
        except Exception:
            non_binary += 1
    likely_pairs = non_binary > len(tokens[: min(2000, len(tokens))]) * 0.3

    if not likely_pairs:
        ba = bytearray(len(tokens))
        for i, t in enumerate(tokens):
            tl = t.strip().lower()
            if tl in ("1", "true", "t"):
                ba[i] = 1
            elif tl in ("0", "false", "f"):
                ba[i] = 0
            else:
                try:
                    ba[i] = 1 if float(tl) != 0.0 else 0
                except Exception:
                    ba[i] = 0
        return ba

    # Parse line-wise, take last token of each non-empty line.
    lines = text.splitlines()
    out = bytearray()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.replace(",", " ").split()
        if not parts:
            continue
        t = parts[-1].strip().lower()
        if t in ("1", "true", "t"):
            out.append(1)
        elif t in ("0", "false", "f"):
            out.append(0)
        else:
            try:
                out.append(1 if float(t) != 0.0 else 0)
            except Exception:
                out.append(0)
    return out


class Solution(MultiRegionStrategy):
    NAME = "trace_aware_wait_then_od_v1"

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

        self._trace_files: List[str] = list(config.get("trace_files", []))
        self._avail: List[bytearray] = []
        self._run_len: List[array] = []
        self._next_true: List[array] = []
        self._trace_len: int = 0

        self._work_done: float = 0.0
        self._last_done_len: int = 0
        self._od_lock_until: float = 0.0
        self._next_region_switch_allowed: float = 0.0
        self._initialized_step_constants: bool = False

        if self._trace_files:
            avails = []
            max_len = 0
            for p in self._trace_files:
                a = _load_trace_file(p)
                avails.append(a)
                if len(a) > max_len:
                    max_len = len(a)
            if max_len == 0:
                self._avail = []
                self._trace_len = 0
            else:
                self._trace_len = max_len
                self._avail = []
                for a in avails:
                    if len(a) < max_len:
                        a = a + bytearray(max_len - len(a))
                    self._avail.append(a)

                self._run_len = []
                self._next_true = []
                for r in range(len(self._avail)):
                    avail = self._avail[r]
                    run = array("I", [0]) * (max_len + 1)
                    nxt = array("I", [0]) * (max_len + 1)
                    nxt[max_len] = max_len
                    for i in range(max_len - 1, -1, -1):
                        if avail[i]:
                            run[i] = run[i + 1] + 1
                            nxt[i] = i
                        else:
                            run[i] = 0
                            nxt[i] = nxt[i + 1]
                    run[max_len] = 0
                    self._run_len.append(run)
                    self._next_true.append(nxt)

        return self

    def _get_scalar(self, x: Any, default: float = 0.0) -> float:
        try:
            if isinstance(x, (list, tuple)):
                return float(x[0]) if x else float(default)
            return float(x)
        except Exception:
            return float(default)

    def _get_task_done_list(self) -> Sequence[float]:
        td = getattr(self, "task_done_time", [])
        if isinstance(td, list) and td and isinstance(td[0], list):
            td = td[0]
        return td if isinstance(td, list) else list(td)

    def _update_work_done(self) -> float:
        td = self._get_task_done_list()
        n = len(td)
        if n < self._last_done_len:
            self._work_done = 0.0
            self._last_done_len = 0
        if n > self._last_done_len:
            s = 0.0
            for v in td[self._last_done_len : n]:
                try:
                    s += float(v)
                except Exception:
                    pass
            self._work_done += s
            self._last_done_len = n
        return self._work_done

    def _time_index(self) -> int:
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            gap = 1.0
        t = float(getattr(self.env, "elapsed_seconds", 0.0))
        return int(t // gap)

    def _region_has_spot_at(self, region: int, idx: int) -> bool:
        if not self._avail:
            return False
        if region < 0 or region >= len(self._avail):
            return False
        if idx < 0 or idx >= self._trace_len:
            return False
        return bool(self._avail[region][idx])

    def _region_run_steps_from(self, region: int, idx: int) -> int:
        if not self._run_len:
            return 0
        if region < 0 or region >= len(self._run_len):
            return 0
        if idx < 0 or idx > self._trace_len:
            return 0
        if idx == self._trace_len:
            return 0
        return int(self._run_len[region][idx])

    def _region_next_spot_idx(self, region: int, idx: int) -> int:
        if not self._next_true:
            return self._trace_len
        if region < 0 or region >= len(self._next_true):
            return self._trace_len
        if idx < 0:
            idx = 0
        if idx > self._trace_len:
            return self._trace_len
        return int(self._next_true[region][idx])

    def _choose_region_for_spot(self, idx: int) -> Optional[int]:
        nreg = int(self.env.get_num_regions())
        if not self._avail or self._trace_len == 0 or nreg <= 0:
            return None

        idx = max(0, min(idx, self._trace_len))

        # Prefer regions with spot at idx and longest subsequent run.
        best_r = None
        best_run = -1
        for r in range(min(nreg, len(self._avail))):
            if idx < self._trace_len and self._avail[r][idx]:
                run = self._region_run_steps_from(r, idx)
                if run > best_run:
                    best_run = run
                    best_r = r
        if best_r is not None:
            return best_r

        # Otherwise pick region with earliest next spot time; tie-break by run length there.
        best_r = None
        best_t = self._trace_len + 1
        best_run = -1
        for r in range(min(nreg, len(self._avail))):
            nt = self._region_next_spot_idx(r, idx)
            if nt >= self._trace_len:
                continue
            run = self._region_run_steps_from(r, nt)
            if nt < best_t or (nt == best_t and run > best_run):
                best_t = nt
                best_run = run
                best_r = r
        return best_r

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        work_done = self._update_work_done()

        task_duration = self._get_scalar(getattr(self, "task_duration", 0.0))
        deadline = self._get_scalar(getattr(self, "deadline", 0.0))
        restart_overhead = self._get_scalar(getattr(self, "restart_overhead", 0.0))
        remaining_restart_overhead = self._get_scalar(getattr(self, "remaining_restart_overhead", 0.0))
        gap = float(getattr(self.env, "gap_seconds", 1.0))
        if gap <= 0:
            gap = 1.0
        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))

        remaining_work = task_duration - work_done
        if remaining_work <= 0:
            return ClusterType.NONE

        time_left = deadline - elapsed
        if time_left <= 0:
            return ClusterType.ON_DEMAND

        slack_total = max(0.0, deadline - task_duration)
        nonprogress_so_far = max(0.0, elapsed - work_done)
        nonprogress_budget_left = slack_total - nonprogress_so_far

        # Panic / must-finish mode: commit to ON_DEMAND to guarantee completion.
        if last_cluster_type == ClusterType.ON_DEMAND:
            min_finish_time_od = remaining_work + max(0.0, remaining_restart_overhead)
        else:
            min_finish_time_od = remaining_work + restart_overhead
        if time_left <= min_finish_time_od + max(gap, 0.25 * restart_overhead) or nonprogress_budget_left <= 0.0:
            self._od_lock_until = deadline + 1.0
            return ClusterType.ON_DEMAND

        # Short lock-in on on-demand to avoid expensive oscillation.
        if last_cluster_type == ClusterType.ON_DEMAND and elapsed < self._od_lock_until:
            return ClusterType.ON_DEMAND

        idx = self._time_index()
        cur_region = int(self.env.get_current_region())

        # If spot available now:
        if has_spot:
            # Consider switching from ON_DEMAND back to SPOT only if it looks stable enough and slack remains.
            if last_cluster_type == ClusterType.ON_DEMAND:
                run_steps = self._region_run_steps_from(cur_region, idx) if self._run_len else 0
                run_seconds = run_steps * gap
                if run_seconds >= 4.0 * restart_overhead and nonprogress_budget_left >= 2.0 * restart_overhead:
                    return ClusterType.SPOT
                else:
                    return ClusterType.ON_DEMAND

            return ClusterType.SPOT

        # No spot available now:
        # If already on-demand, keep it.
        if last_cluster_type == ClusterType.ON_DEMAND:
            return ClusterType.ON_DEMAND

        # If slack is still ample, pause (free) and switch region to chase spot availability.
        # If slack is getting low, move to ON_DEMAND.
        if nonprogress_budget_left >= 2.5 * restart_overhead and time_left > remaining_work + 1.5 * restart_overhead:
            # Avoid region switching while restart overhead is pending (it may reset overhead).
            if remaining_restart_overhead <= 0.0 and elapsed >= self._next_region_switch_allowed:
                target = self._choose_region_for_spot(idx + 1)
                if target is not None and target != cur_region:
                    try:
                        self.env.switch_region(int(target))
                        self._next_region_switch_allowed = elapsed + max(gap, 0.5 * restart_overhead)
                    except Exception:
                        pass
            return ClusterType.NONE

        # Enter on-demand and hold it for at least one overhead window.
        self._od_lock_until = elapsed + max(gap, restart_overhead)
        return ClusterType.ON_DEMAND
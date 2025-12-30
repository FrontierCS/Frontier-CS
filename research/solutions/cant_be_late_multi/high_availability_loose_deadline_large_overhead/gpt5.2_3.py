import json
import os
import math
from argparse import Namespace
from array import array
from typing import List, Optional, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_multi_region_v1"

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

        self._spec_path = spec_path
        self._base_dir = os.path.dirname(os.path.abspath(spec_path))
        self._trace_paths: List[str] = []
        self._spot_traces: List[bytearray] = []
        self._next_unavail: List[array] = []
        self._trace_num_regions: int = 0

        self._work_done_total = 0.0
        self._last_task_done_len = 0

        self._committed_ondemand = False
        self._initialized = False

        trace_files = config.get("trace_files", [])
        if isinstance(trace_files, list) and trace_files:
            for p in trace_files:
                if not isinstance(p, str):
                    continue
                ap = p if os.path.isabs(p) else os.path.join(self._base_dir, p)
                self._trace_paths.append(ap)

            self._spot_traces = []
            for ap in self._trace_paths:
                try:
                    self._spot_traces.append(self._load_trace(ap))
                except Exception:
                    self._spot_traces.append(bytearray())

            self._trace_num_regions = len(self._spot_traces)
            self._next_unavail = []
            for tr in self._spot_traces:
                if not tr:
                    self._next_unavail.append(array("I", [0]))
                    continue
                n = len(tr)
                nxt = array("I", [0]) * (n + 1)
                nxt[n] = n
                for i in range(n - 1, -1, -1):
                    if tr[i] == 0:
                        nxt[i] = i
                    else:
                        nxt[i] = nxt[i + 1]
                self._next_unavail.append(nxt)

        return self

    def _load_trace(self, path: str) -> bytearray:
        with open(path, "r") as f:
            s = f.read()

        ss = s.lstrip()
        if not ss:
            return bytearray()

        if ss[0] in "[{":
            data = json.loads(ss)
            arr = None
            if isinstance(data, list):
                arr = data
            elif isinstance(data, dict):
                for k in ("trace", "availability", "avail", "spot", "data", "values"):
                    v = data.get(k, None)
                    if isinstance(v, list):
                        arr = v
                        break
                if arr is None:
                    for v in data.values():
                        if isinstance(v, list):
                            arr = v
                            break
            if arr is None:
                return bytearray()
            out = bytearray()
            for x in arr:
                if isinstance(x, bool):
                    out.append(1 if x else 0)
                else:
                    try:
                        fx = float(x)
                    except Exception:
                        continue
                    out.append(1 if fx > 0.0 else 0)
            return out

        out = bytearray()
        for line in s.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "#" in line:
                line = line.split("#", 1)[0].strip()
                if not line:
                    continue
            line = line.replace(",", " ")
            parts = line.split()
            if not parts:
                continue
            tok = parts[-1].strip()
            tl = tok.lower()
            if tl in ("1", "true", "t", "yes", "y"):
                out.append(1)
            elif tl in ("0", "false", "f", "no", "n"):
                out.append(0)
            else:
                try:
                    fx = float(tok)
                except Exception:
                    continue
                out.append(1 if fx > 0.0 else 0)
        return out

    def _lazy_init(self) -> None:
        if self._initialized:
            return

        self._gap = float(getattr(self.env, "gap_seconds", 1.0))

        td = getattr(self, "task_duration", None)
        if td is None:
            td = getattr(self, "task_durations", None)
            if isinstance(td, (list, tuple)) and td:
                td = td[0]
        if td is None:
            td = getattr(self, "task_duration_seconds", None)
        self._task_duration_s = float(td) if td is not None else 0.0

        dl = getattr(self, "deadline", None)
        if dl is None:
            dl = getattr(self, "deadlines", None)
            if isinstance(dl, (list, tuple)) and dl:
                dl = dl[0]
        if dl is None:
            dl = getattr(self, "deadline_seconds", None)
        self._deadline_s = float(dl) if dl is not None else 0.0

        ro = getattr(self, "restart_overhead", None)
        if ro is None:
            ro = getattr(self, "restart_overheads", None)
            if isinstance(ro, (list, tuple)) and ro:
                ro = ro[0]
        if ro is None:
            ro = getattr(self, "restart_overhead_seconds", None)
        self._restart_overhead_s = float(ro) if ro is not None else 0.0

        self._switch_worthwhile_delta_s = 2.0 * self._restart_overhead_s

        self._initialized = True

    def _update_work_done(self) -> None:
        td = self.task_done_time
        l = len(td)
        if l > self._last_task_done_len:
            inc = 0.0
            for i in range(self._last_task_done_len, l):
                inc += float(td[i])
            self._work_done_total += inc
            self._last_task_done_len = l

    def _time_index(self, elapsed_s: float) -> int:
        g = self._gap
        if g <= 0:
            return 0
        return int(elapsed_s / g + 1e-12)

    def _spot_avail_and_run_s(self, region: int, t: int) -> Tuple[bool, float]:
        if region < 0 or region >= len(self._spot_traces):
            return False, 0.0
        tr = self._spot_traces[region]
        if not tr:
            return False, 0.0
        n = len(tr)
        if n <= 0:
            return False, 0.0
        if t < 0:
            t = 0
        if t >= n:
            t = n - 1
        if tr[t] == 0:
            return False, 0.0
        nxt = self._next_unavail[region]
        run_steps = int(nxt[t] - t) if t < len(nxt) else 1
        if run_steps < 1:
            run_steps = 1
        return True, run_steps * self._gap

    def _best_spot_region(self, t: int, cur_region: int, num_regions: int) -> Tuple[int, float, float]:
        best_r = -1
        best_run_s = 0.0
        cur_run_s = 0.0

        if 0 <= cur_region < num_regions:
            ok, rs = self._spot_avail_and_run_s(cur_region, t)
            if ok:
                cur_run_s = rs

        for r in range(num_regions):
            ok, rs = self._spot_avail_and_run_s(r, t)
            if not ok:
                continue
            if rs > best_run_s:
                best_run_s = rs
                best_r = r

        return best_r, best_run_s, cur_run_s

    def _required_time_on_demand_s(self, remaining_work_s: float, last_cluster_type: ClusterType) -> float:
        gap = self._gap
        if gap <= 0:
            return float("inf")
        if last_cluster_type == ClusterType.ON_DEMAND:
            overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        else:
            overhead = self._restart_overhead_s
        need = remaining_work_s + max(0.0, overhead)
        if need <= 0.0:
            return 0.0
        steps = int((need + gap - 1e-9) // gap)
        if steps < 1:
            steps = 1
        return steps * gap

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._lazy_init()
        self._update_work_done()

        remaining_work = self._task_duration_s - self._work_done_total
        if remaining_work <= 1e-9:
            return ClusterType.NONE

        elapsed = float(getattr(self.env, "elapsed_seconds", 0.0))
        time_left = self._deadline_s - elapsed
        if time_left <= 1e-9:
            return ClusterType.NONE

        if self._committed_ondemand:
            return ClusterType.ON_DEMAND

        gap = self._gap
        required_time_od = self._required_time_on_demand_s(remaining_work, last_cluster_type)
        emergency_buffer = 2.0 * gap
        if time_left <= required_time_od + emergency_buffer:
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        pending_overhead = float(getattr(self, "remaining_restart_overhead", 0.0) or 0.0)
        if pending_overhead > 1e-9:
            if last_cluster_type == ClusterType.ON_DEMAND:
                return ClusterType.ON_DEMAND
            if last_cluster_type == ClusterType.SPOT:
                if self._spot_traces:
                    cur_region = self.env.get_current_region() if hasattr(self.env, "get_current_region") else 0
                    t = self._time_index(elapsed)
                    ok, _ = self._spot_avail_and_run_s(cur_region, t)
                    if ok:
                        return ClusterType.SPOT
                else:
                    if has_spot:
                        return ClusterType.SPOT
            if last_cluster_type == ClusterType.NONE:
                if self._spot_traces:
                    cur_region = self.env.get_current_region() if hasattr(self.env, "get_current_region") else 0
                    t = self._time_index(elapsed)
                    ok, _ = self._spot_avail_and_run_s(cur_region, t)
                    if ok:
                        return ClusterType.SPOT
                else:
                    if has_spot:
                        return ClusterType.SPOT
                if time_left >= required_time_od + gap:
                    return ClusterType.NONE
                self._committed_ondemand = True
                return ClusterType.ON_DEMAND

        cur_region = self.env.get_current_region() if hasattr(self.env, "get_current_region") else 0
        if hasattr(self.env, "get_num_regions"):
            env_regions = int(self.env.get_num_regions())
        else:
            env_regions = self._trace_num_regions if self._trace_num_regions > 0 else 1
        trace_regions = self._trace_num_regions if self._trace_num_regions > 0 else env_regions
        num_regions = env_regions if trace_regions <= 0 else min(env_regions, trace_regions)
        if num_regions <= 0:
            num_regions = 1

        t = self._time_index(elapsed)

        if self._spot_traces and num_regions > 0:
            best_r, best_run_s, cur_run_s = self._best_spot_region(t, cur_region, num_regions)

            if best_r != -1:
                if last_cluster_type == ClusterType.SPOT and cur_run_s > 0.0:
                    if best_r == cur_region:
                        return ClusterType.SPOT
                    if best_run_s - cur_run_s > self._switch_worthwhile_delta_s:
                        try:
                            self.env.switch_region(best_r)
                        except Exception:
                            pass
                        return ClusterType.SPOT
                    return ClusterType.SPOT

                if last_cluster_type == ClusterType.ON_DEMAND:
                    min_run_to_switch = max(2.0 * gap, 2.0 * self._restart_overhead_s)
                    extra_slack = time_left - required_time_od
                    if best_run_s >= min_run_to_switch and extra_slack >= 6.0 * gap:
                        if best_r != cur_region:
                            try:
                                self.env.switch_region(best_r)
                            except Exception:
                                pass
                        return ClusterType.SPOT
                    return ClusterType.ON_DEMAND

                if best_r != cur_region:
                    try:
                        self.env.switch_region(best_r)
                    except Exception:
                        pass
                return ClusterType.SPOT

            if time_left >= required_time_od + gap:
                return ClusterType.NONE
            self._committed_ondemand = True
            return ClusterType.ON_DEMAND

        if has_spot:
            return ClusterType.SPOT

        if time_left >= required_time_od + gap:
            return ClusterType.NONE
        self._committed_ondemand = True
        return ClusterType.ON_DEMAND
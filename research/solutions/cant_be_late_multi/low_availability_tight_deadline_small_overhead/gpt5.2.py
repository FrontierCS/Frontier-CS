import json
import os
import re
from argparse import Namespace
from array import array
from typing import Any, Callable, List, Optional, Sequence, Tuple

from sky_spot.strategies.multi_strategy import MultiRegionStrategy
from sky_spot.utils import ClusterType


class Solution(MultiRegionStrategy):
    NAME = "cant_be_late_v1"

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

        self._trace_files: List[str] = list(config.get("trace_files", []) or [])
        self._traces: Optional[List[bytearray]] = None
        self._runlens: Optional[List[array]] = None
        self._use_traces: bool = False
        self._traces_validated: bool = False
        self._traces_invalid: bool = False

        self._done_sum: float = 0.0
        self._done_len: int = 0

        self._num_regions: Optional[int] = None
        self._region_score: Optional[List[float]] = None
        self._alpha: float = 0.05

        self._committed_ondemand: bool = False
        self._no_spot_streak: int = 0

        self._ct_spot = self._ct_by_name("SPOT")
        self._ct_ond = self._ct_by_name("ON_DEMAND")
        self._ct_none = self._ct_by_name("NONE")

        self._region_spot_query: Optional[Callable[[int], Any]] = None
        self._all_regions_spot_query: Optional[Callable[[], Any]] = None

        self._loaded_traces_ok: bool = False
        if self._trace_files:
            try:
                traces: List[bytearray] = []
                for p in self._trace_files:
                    traces.append(self._load_trace_to_bytearray(p))
                self._traces = traces
                self._runlens = [self._compute_runlen(tr) for tr in traces]
                self._use_traces = True
                self._loaded_traces_ok = True
            except Exception:
                self._traces = None
                self._runlens = None
                self._use_traces = False
                self._loaded_traces_ok = False

        return self

    def _ct_by_name(self, name: str) -> ClusterType:
        if hasattr(ClusterType, name):
            return getattr(ClusterType, name)
        lname = name.lower()
        for m in ClusterType:
            if getattr(m, "name", "").lower() == lname:
                return m
        for m in ClusterType:
            if getattr(m, "name", "").lower().replace("_", "") == lname.replace("_", ""):
                return m
        return list(ClusterType)[0]

    def _load_trace_to_bytearray(self, path: str) -> bytearray:
        ext = os.path.splitext(path)[1].lower()
        if ext == ".npy":
            try:
                import numpy as np  # type: ignore

                arr = np.load(path)
                flat = arr.reshape(-1)
                out = bytearray(len(flat))
                for i, v in enumerate(flat):
                    out[i] = 1 if float(v) > 0.5 else 0
                if not out:
                    raise ValueError("empty npy trace")
                return out
            except Exception:
                pass

        try:
            with open(path, "r") as f:
                data = json.load(f)
            seq = None
            if isinstance(data, list):
                seq = data
            elif isinstance(data, dict):
                for k in ("availability", "avail", "spot", "has_spot", "trace", "data"):
                    if k in data and isinstance(data[k], list):
                        seq = data[k]
                        break
            if seq is None:
                raise ValueError("unrecognized json trace")
            out = bytearray(len(seq))
            for i, v in enumerate(seq):
                try:
                    out[i] = 1 if float(v) > 0.5 else 0
                except Exception:
                    out[i] = 1 if bool(v) else 0
            if not out:
                raise ValueError("empty json trace")
            return out
        except Exception:
            pass

        nums: List[int] = []
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = re.split(r"[,\s]+", line)
                last_num = None
                for p in reversed(parts):
                    try:
                        last_num = float(p)
                        break
                    except Exception:
                        continue
                if last_num is None:
                    continue
                nums.append(1 if last_num > 0.5 else 0)

        if not nums:
            raise ValueError(f"failed to parse trace: {path}")
        return bytearray(nums)

    def _compute_runlen(self, tr: bytearray) -> array:
        n = len(tr)
        run = array("I", [0]) * (n + 1)
        for i in range(n - 1, -1, -1):
            run[i] = (run[i + 1] + 1) if tr[i] else 0
        return run

    def _ensure_runtime_init(self) -> None:
        if self._num_regions is None:
            try:
                self._num_regions = int(self.env.get_num_regions())
            except Exception:
                self._num_regions = 1

            self._region_score = [0.5] * self._num_regions

            if self._use_traces and self._traces is not None:
                if len(self._traces) != self._num_regions:
                    self._use_traces = False
                    self._traces_invalid = True

            self._setup_spot_query_functions()

    def _setup_spot_query_functions(self) -> None:
        env = self.env
        region_methods = (
            "get_spot_availability",
            "get_spot_available",
            "has_spot_in_region",
            "region_has_spot",
            "get_region_has_spot",
        )
        for name in region_methods:
            fn = getattr(env, name, None)
            if callable(fn):
                try:
                    v = fn(0)
                    if isinstance(v, (bool, int)):
                        self._region_spot_query = fn
                        break
                except TypeError:
                    continue
                except Exception:
                    continue

        all_methods = (
            "get_spot_availabilities",
            "get_all_spot_availabilities",
            "get_spot_availability_all_regions",
            "get_spot_available_regions",
        )
        for name in all_methods:
            fn = getattr(env, name, None)
            if callable(fn):
                try:
                    v = fn()
                    if isinstance(v, (list, tuple)) and v:
                        self._all_regions_spot_query = fn
                        break
                except TypeError:
                    continue
                except Exception:
                    continue

    def _update_done_sum(self) -> None:
        td = self.task_done_time
        l = len(td)
        if l > self._done_len:
            self._done_sum += float(sum(td[self._done_len : l]))
            self._done_len = l

    def _trace_spot(self, region: int, t_idx: int) -> bool:
        if not self._use_traces or self._traces is None:
            return False
        if region < 0 or region >= len(self._traces):
            return False
        tr = self._traces[region]
        if t_idx < 0 or t_idx >= len(tr):
            return False
        return bool(tr[t_idx])

    def _runlen(self, region: int, t_idx: int) -> int:
        if not self._use_traces or self._runlens is None:
            return 0
        if region < 0 or region >= len(self._runlens):
            return 0
        rl = self._runlens[region]
        if t_idx < 0 or t_idx >= len(rl):
            return 0
        return int(rl[t_idx])

    def _pick_best_region_by_traces(self, t_idx: int) -> Optional[int]:
        if not self._use_traces or self._traces is None or self._runlens is None or self._num_regions is None:
            return None
        best_r = None
        best_len = 0
        for r in range(self._num_regions):
            if self._trace_spot(r, t_idx):
                rl = self._runlen(r, t_idx)
                if rl > best_len:
                    best_len = rl
                    best_r = r
        return best_r

    def _pick_best_region_by_score(self) -> int:
        assert self._region_score is not None
        best_r = 0
        best_s = self._region_score[0]
        for i, s in enumerate(self._region_score[1:], start=1):
            if s > best_s:
                best_s = s
                best_r = i
        return best_r

    def _switch_region_safely(self, target: int) -> None:
        try:
            cur = int(self.env.get_current_region())
        except Exception:
            cur = 0
        if target == cur:
            return
        try:
            self.env.switch_region(int(target))
        except Exception:
            pass

    def _get_commit_buffer(self) -> float:
        g = float(getattr(self.env, "gap_seconds", 1.0))
        h = float(self.restart_overhead)
        return h + (g if g > 2.0 * h else 2.0 * h)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._ensure_runtime_init()
        self._update_done_sum()

        time_left = float(self.deadline) - float(self.env.elapsed_seconds)
        if time_left <= 0:
            return self._ct_none

        remaining_work = float(self.task_duration) - float(self._done_sum)
        if remaining_work <= 0:
            return self._ct_none

        g = float(getattr(self.env, "gap_seconds", 1.0))
        commit_buffer = self._get_commit_buffer()

        overhead_to_start_ond = 0.0 if last_cluster_type == self._ct_ond else float(self.restart_overhead)
        slack_if_ond_now = time_left - remaining_work - overhead_to_start_ond

        try:
            cur_region = int(self.env.get_current_region())
        except Exception:
            cur_region = 0

        if self._region_score is not None and 0 <= cur_region < len(self._region_score):
            x = 1.0 if has_spot else 0.0
            self._region_score[cur_region] = (1.0 - self._alpha) * self._region_score[cur_region] + self._alpha * x

        if self._use_traces and not self._traces_invalid and self._traces is not None:
            t_idx = int(float(self.env.elapsed_seconds) // g) if g > 0 else 0
            if 0 <= cur_region < len(self._traces) and 0 <= t_idx < len(self._traces[cur_region]):
                if bool(self._traces[cur_region][t_idx]) != bool(has_spot):
                    self._traces_invalid = True
                    self._use_traces = False
                    self._traces = None
                    self._runlens = None

        if self._committed_ondemand or slack_if_ond_now <= commit_buffer:
            self._committed_ondemand = True
            return self._ct_ond

        if has_spot:
            self._no_spot_streak = 0
            return self._ct_spot

        self._no_spot_streak += 1

        t_idx = int(float(self.env.elapsed_seconds) // g) if g > 0 else 0

        if self._use_traces and not self._traces_invalid:
            best_r = self._pick_best_region_by_traces(t_idx)
            if best_r is not None and best_r != cur_region:
                if slack_if_ond_now > commit_buffer + g:
                    self._switch_region_safely(best_r)
                return self._ct_none

        if self._all_regions_spot_query is not None and self._num_regions is not None:
            try:
                v = self._all_regions_spot_query()
                if isinstance(v, (list, tuple)) and len(v) >= self._num_regions:
                    for r in range(self._num_regions):
                        if bool(v[r]):
                            self._switch_region_safely(r)
                            return self._ct_spot
            except Exception:
                pass

        if self._region_spot_query is not None and self._num_regions is not None:
            try:
                best = None
                for r in range(self._num_regions):
                    if bool(self._region_spot_query(r)):
                        best = r
                        break
                if best is not None:
                    self._switch_region_safely(best)
                    return self._ct_spot
            except Exception:
                pass

        if slack_if_ond_now > commit_buffer + g and self._num_regions is not None and self._region_score is not None:
            target = self._pick_best_region_by_score()
            if target != cur_region:
                self._switch_region_safely(target)
            return self._ct_none

        self._committed_ondemand = True
        return self._ct_ond
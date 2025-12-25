import json
from typing import Any, Dict, Optional, Sequence, Tuple

from sky_spot.strategies.strategy import Strategy
from sky_spot.utils import ClusterType


class Solution(Strategy):
    NAME = "cant_be_late_lazy_spot_v2"

    def __init__(self, args=None):
        super().__init__(args)
        self._spec: Dict[str, Any] = {}

        self._td_cache_id: int = 0
        self._td_cache_len: int = 0
        self._td_cache_sum: float = 0.0
        self._td_cache_nondec: bool = True
        self._td_cache_last: float = 0.0
        self._td_cache_max: float = 0.0

    def solve(self, spec_path: str) -> "Solution":
        self._spec = {}
        if spec_path:
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    txt = f.read()
                try:
                    self._spec = json.loads(txt)
                except Exception:
                    self._spec = self._parse_simple_yaml(txt)
            except Exception:
                self._spec = {}
        return self

    def _parse_simple_yaml(self, txt: str) -> Dict[str, Any]:
        d: Dict[str, Any] = {}
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            k, v = line.split(":", 1)
            k = k.strip()
            v = v.strip()
            if not k:
                continue
            vl = v.lower()
            if vl == "true":
                d[k] = True
                continue
            if vl == "false":
                d[k] = False
                continue
            try:
                if any(c in v for c in (".", "e", "E")):
                    d[k] = float(v)
                else:
                    d[k] = int(v)
            except Exception:
                d[k] = v.strip("\"'")
        return d

    def _get_completed_seconds(self) -> float:
        td = getattr(self, "task_done_time", None)
        if td is None:
            return 0.0
        if isinstance(td, (int, float)):
            return float(td)
        if not td:
            return 0.0

        try:
            seq: Sequence[Any] = td  # type: ignore[assignment]
            tid = id(seq)
            n = len(seq)  # type: ignore[arg-type]
        except Exception:
            return 0.0

        if tid != self._td_cache_id or n < self._td_cache_len:
            s = 0.0
            nondec = True
            last = None
            mx = float("-inf")
            for x in seq:
                try:
                    fx = float(x)
                except Exception:
                    continue
                s += fx
                if last is not None and fx < last - 1e-9:
                    nondec = False
                last = fx
                if fx > mx:
                    mx = fx
            self._td_cache_id = tid
            self._td_cache_len = n
            self._td_cache_sum = s
            self._td_cache_nondec = nondec
            self._td_cache_last = float(last) if last is not None else 0.0
            self._td_cache_max = 0.0 if mx == float("-inf") else float(mx)
        else:
            s = self._td_cache_sum
            nondec = self._td_cache_nondec
            last = self._td_cache_last
            mx = self._td_cache_max

            for i in range(self._td_cache_len, n):
                try:
                    fx = float(seq[i])  # type: ignore[index]
                except Exception:
                    continue
                s += fx
                if fx < last - 1e-9:
                    nondec = False
                last = fx
                if fx > mx:
                    mx = fx

            self._td_cache_len = n
            self._td_cache_sum = s
            self._td_cache_nondec = nondec
            self._td_cache_last = last
            self._td_cache_max = mx

        env = getattr(self, "env", None)
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)
        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)

        sum_td = self._td_cache_sum
        nondec = self._td_cache_nondec
        last = self._td_cache_last
        mx = self._td_cache_max

        if task_dur > 0.0 and sum_td > task_dur + max(gap, 1.0):
            completed = last if nondec else mx
        else:
            completed = sum_td

        if task_dur > 0.0:
            if completed < 0.0:
                completed = 0.0
            elif completed > task_dur:
                completed = task_dur
        return float(completed)

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        env = getattr(self, "env", None)
        elapsed = float(getattr(env, "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(env, "gap_seconds", 0.0) or 0.0)

        task_dur = float(getattr(self, "task_duration", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        completed = self._get_completed_seconds()
        remaining_work = task_dur - completed
        if remaining_work <= 1e-6:
            return ClusterType.NONE

        remaining_time = deadline - elapsed
        if remaining_time <= 0.0:
            return ClusterType.SPOT if has_spot else ClusterType.ON_DEMAND

        overhead_to_od = 0.0 if last_cluster_type == ClusterType.ON_DEMAND else restart

        safety = max(gap, restart) * 2.0 + 1.0
        slack = remaining_time - remaining_work

        must_od_now = (remaining_work + overhead_to_od + safety) >= remaining_time
        if must_od_now:
            return ClusterType.ON_DEMAND

        if has_spot:
            if last_cluster_type == ClusterType.ON_DEMAND:
                switch_threshold = 2.0 * restart + safety
                if slack <= switch_threshold:
                    return ClusterType.ON_DEMAND
            return ClusterType.SPOT

        if last_cluster_type == ClusterType.ON_DEMAND:
            pause_threshold = restart + safety + max(gap, 1.0)
            if slack > pause_threshold:
                return ClusterType.NONE
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)
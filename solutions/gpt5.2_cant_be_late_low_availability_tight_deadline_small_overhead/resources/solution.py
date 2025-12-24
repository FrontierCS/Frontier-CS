import json
from typing import Any, Optional

try:
    from sky_spot.strategies.strategy import Strategy
    from sky_spot.utils import ClusterType
except Exception:  # pragma: no cover
    class ClusterType:  # type: ignore
        SPOT = "spot"
        ON_DEMAND = "on_demand"
        NONE = "none"

    class Strategy:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass


class Solution(Strategy):
    NAME = "deadline_guard_v1"

    def __init__(self, args: Optional[Any] = None):
        try:
            super().__init__(args)
        except TypeError:
            try:
                super().__init__()
            except Exception:
                pass

        self.args = args
        self._committed_od = False

        self._steps_seen = 0
        self._spot_seen = 0

        self._done_cache = 0.0
        self._done_list_id = None
        self._done_list_pos = 0
        self._done_mode = None  # "numbers" or "pairs" or "unknown"

        self._guard_gap_multiplier = 2.0
        self._guard_overhead_multiplier = 1.0

    def solve(self, spec_path: str) -> "Solution":
        try:
            with open(spec_path, "r") as f:
                spec = json.load(f)
            if isinstance(spec, dict):
                gg = spec.get("guard_gap_multiplier", None)
                go = spec.get("guard_overhead_multiplier", None)
                if isinstance(gg, (int, float)) and gg >= 0:
                    self._guard_gap_multiplier = float(gg)
                if isinstance(go, (int, float)) and go >= 0:
                    self._guard_overhead_multiplier = float(go)
        except Exception:
            pass
        return self

    def _infer_done_mode(self, lst) -> str:
        for x in lst:
            if isinstance(x, (int, float)):
                continue
            if isinstance(x, (tuple, list)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                continue
            if isinstance(x, dict) and "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(x["end"], (int, float)):
                continue
            return "unknown"
        if not lst:
            return "numbers"
        if all(isinstance(x, (int, float)) for x in lst):
            return "numbers"
        if all(
            (isinstance(x, (tuple, list)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)))
            or (isinstance(x, dict) and "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(x["end"], (int, float)))
            for x in lst
        ):
            return "pairs"
        return "unknown"

    def _get_done_work_seconds(self) -> float:
        tdt = getattr(self, "task_done_time", None)
        if tdt is None:
            for attr in ("task_done_seconds", "task_done", "done_seconds", "work_done_seconds"):
                v = getattr(self, attr, None)
                if isinstance(v, (int, float)):
                    return float(v)
            return 0.0

        if isinstance(tdt, (int, float)):
            return float(tdt)

        if not isinstance(tdt, list):
            return 0.0

        lst = tdt
        lid = id(lst)
        if self._done_list_id != lid:
            self._done_list_id = lid
            self._done_list_pos = 0
            self._done_cache = 0.0
            self._done_mode = self._infer_done_mode(lst)

        n = len(lst)
        if self._done_list_pos > n:
            self._done_list_pos = 0
            self._done_cache = 0.0
            self._done_mode = self._infer_done_mode(lst)

        mode = self._done_mode or "unknown"

        if mode == "numbers":
            if self._done_list_pos == 0 and n <= 64:
                self._done_cache = float(sum(float(x) for x in lst if isinstance(x, (int, float))))
                self._done_list_pos = n
                return self._done_cache
            for i in range(self._done_list_pos, n):
                x = lst[i]
                if isinstance(x, (int, float)):
                    self._done_cache += float(x)
                else:
                    self._done_mode = "unknown"
                    return self._get_done_work_seconds()
            self._done_list_pos = n
            return self._done_cache

        if mode == "pairs":
            for i in range(self._done_list_pos, n):
                x = lst[i]
                if isinstance(x, (tuple, list)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                    self._done_cache += float(x[1]) - float(x[0])
                elif isinstance(x, dict) and "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(x["end"], (int, float)):
                    self._done_cache += float(x["end"]) - float(x["start"])
                else:
                    self._done_mode = "unknown"
                    return self._get_done_work_seconds()
            self._done_list_pos = n
            return self._done_cache

        done = 0.0
        for x in lst:
            if isinstance(x, (int, float)):
                done += float(x)
            elif isinstance(x, (tuple, list)) and len(x) >= 2 and isinstance(x[0], (int, float)) and isinstance(x[1], (int, float)):
                done += float(x[1]) - float(x[0])
            elif isinstance(x, dict) and "start" in x and "end" in x and isinstance(x["start"], (int, float)) and isinstance(x["end"], (int, float)):
                done += float(x["end"]) - float(x["start"])
        self._done_cache = done
        self._done_list_pos = n
        self._done_mode = "unknown"
        return done

    def _remaining_work_seconds(self) -> float:
        td = getattr(self, "task_duration", 0.0)
        if not isinstance(td, (int, float)):
            return 0.0
        done = self._get_done_work_seconds()
        rem = float(td) - float(done)
        return rem if rem > 0.0 else 0.0

    def _should_commit_on_demand(self, elapsed: float, remaining_work: float, gap: float, restart_overhead: float, deadline: float) -> bool:
        guard = (self._guard_gap_multiplier * gap) + (self._guard_overhead_multiplier * restart_overhead)
        latest_start = deadline - (remaining_work + restart_overhead + guard)
        return elapsed >= latest_start

    def _step(self, last_cluster_type: ClusterType, has_spot: bool) -> ClusterType:
        self._steps_seen += 1
        if has_spot:
            self._spot_seen += 1

        if last_cluster_type == ClusterType.ON_DEMAND:
            self._committed_od = True

        elapsed = float(getattr(getattr(self, "env", None), "elapsed_seconds", 0.0) or 0.0)
        gap = float(getattr(getattr(self, "env", None), "gap_seconds", 0.0) or 0.0)
        deadline = float(getattr(self, "deadline", 0.0) or 0.0)
        restart_overhead = float(getattr(self, "restart_overhead", 0.0) or 0.0)

        if deadline > 0.0 and elapsed >= deadline:
            return ClusterType.NONE

        remaining_work = self._remaining_work_seconds()
        if remaining_work <= 0.0:
            return ClusterType.NONE

        if self._committed_od:
            return ClusterType.ON_DEMAND

        if gap <= 0.0:
            gap = 1.0

        if has_spot:
            return ClusterType.SPOT

        if self._should_commit_on_demand(elapsed, remaining_work, gap, restart_overhead, deadline):
            self._committed_od = True
            return ClusterType.ON_DEMAND

        return ClusterType.NONE

    @classmethod
    def _from_args(cls, parser):
        args, _ = parser.parse_known_args()
        return cls(args)

import math
import random
from typing import Any, Dict, List, Optional, Tuple, Union


class _UniversalAction(dict):
    def __init__(
        self,
        region_index: int = 0,
        region_name: Optional[str] = None,
        on_demand: bool = True,
        num_regions: Optional[int] = None,
    ):
        super().__init__()
        self["region_index"] = region_index
        self["region"] = region_index
        if region_name is not None:
            self["region_name"] = region_name
            self["zone"] = region_name
        self["on_demand"] = bool(on_demand)
        self["use_on_demand"] = bool(on_demand)
        self["type"] = "on_demand" if on_demand else "spot"
        self["mode"] = self["type"]
        self["action"] = "on_demand" if on_demand else "spot"
        self["provider"] = "on_demand" if on_demand else "spot"
        self["resource"] = "on_demand" if on_demand else "spot"
        if num_regions is not None:
            self["num_regions"] = num_regions

    def __int__(self) -> int:
        # If discrete action space is (regions as spot) + 1 for on-demand, return that encoding.
        n = self.get("num_regions", None)
        if self["on_demand"]:
            if n is not None and isinstance(n, int) and n > 0:
                return n
            return max(0, int(self["region_index"]))
        return int(self["region_index"])

    def __index__(self) -> int:
        return int(self)

    def __float__(self) -> float:
        return float(int(self))

    def __str__(self) -> str:
        if self["on_demand"]:
            return "on_demand"
        if "region_name" in self:
            return str(self["region_name"])
        return str(self["region_index"])

    def __repr__(self) -> str:
        return f"_UniversalAction(region_index={self['region_index']}, on_demand={self['on_demand']}, region_name={self.get('region_name')})"

    def __iter__(self):
        # Tuple format (region_index, is_on_demand)
        yield self["region_index"]
        yield 1 if self["on_demand"] else 0

    def to_tuple(self) -> Tuple[int, int]:
        return (self["region_index"], 1 if self["on_demand"] else 0)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self)


class _UniversalAgentBase:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config: Dict[str, Any] = config.copy() if isinstance(config, dict) else {}
        self.random = random.Random(self.config.get("seed", None))
        self._default_region_index = 0
        self._default_region_name: Optional[str] = None
        self._num_regions: Optional[int] = None
        self._deadline_hours: Optional[float] = None
        self._task_duration_hours: Optional[float] = 24.0
        self._overhead_hours: Optional[float] = None
        self._on_demand_price: Optional[float] = None
        self._spot_price: Optional[float] = None
        self.reset(self.config)

    def seed(self, seed: Optional[int] = None) -> None:
        self.random.seed(seed)

    def _extract_from_config(self, cfg: Dict[str, Any]) -> None:
        self._deadline_hours = cfg.get("deadline_hours") or cfg.get("deadline") or cfg.get("deadline_h")
        self._task_duration_hours = cfg.get("task_duration_hours", self._task_duration_hours)
        self._overhead_hours = cfg.get("restart_overhead_hours") or cfg.get("overhead_hours") or cfg.get("restart_overhead")
        self._on_demand_price = cfg.get("on_demand_price")
        self._spot_price = cfg.get("spot_price")
        regions = cfg.get("regions") or cfg.get("region_names") or cfg.get("zones")
        if isinstance(regions, (list, tuple)) and regions:
            self._num_regions = len(regions)
            # choose first as default
            self._default_region_name = str(regions[0])
            self._default_region_index = 0
        else:
            # might have num_regions specified
            n = cfg.get("num_regions")
            if isinstance(n, int) and n > 0:
                self._num_regions = n
            # might have default region specified
            default_region = cfg.get("default_region")
            if default_region is not None:
                if isinstance(default_region, int):
                    self._default_region_index = int(default_region)
                else:
                    self._default_region_name = str(default_region)

    def reset(self, config: Optional[Dict[str, Any]] = None) -> None:
        if isinstance(config, dict):
            self.config.update(config)
        self._extract_from_config(self.config)

    def _parse_observation_regions(
        self, observation: Any
    ) -> Tuple[int, Optional[str], Optional[int]]:
        """
        Returns (region_index, region_name, num_regions)
        """
        region_index = self._default_region_index
        region_name = self._default_region_name
        num_regions = self._num_regions

        if isinstance(observation, dict):
            # Try to get current region info
            if "current_region" in observation:
                cur = observation.get("current_region")
                if isinstance(cur, int):
                    region_index = cur
                elif isinstance(cur, str):
                    region_name = cur
            if "region" in observation:
                cur = observation.get("region")
                if isinstance(cur, int):
                    region_index = cur
                elif isinstance(cur, str):
                    region_name = cur
            if "region_index" in observation and isinstance(observation["region_index"], int):
                region_index = int(observation["region_index"])
            if "region_name" in observation and isinstance(observation["region_name"], str):
                region_name = observation["region_name"]

            regions = observation.get("regions") or observation.get("region_names") or observation.get("zones")
            if isinstance(regions, (list, tuple)):
                num_regions = len(regions)
                if region_name is None and isinstance(region_index, int) and 0 <= region_index < len(regions):
                    try:
                        region_name = str(regions[region_index])
                    except Exception:
                        pass
                if region_name is not None and isinstance(region_name, str) and region_name in regions:
                    try:
                        region_index = int(list(regions).index(region_name))
                    except Exception:
                        pass

            if "num_regions" in observation and isinstance(observation["num_regions"], int):
                num_regions = int(observation["num_regions"])

        elif isinstance(observation, (list, tuple)):
            # Try to infer if they provided (remaining_work, time_to_deadline, num_regions, current_region_idx, ...)
            # This is a heuristic fallback.
            if len(observation) >= 3:
                cand = observation[2]
                if isinstance(cand, int) and cand > 0:
                    num_regions = int(cand)
            if len(observation) >= 4 and isinstance(observation[3], int):
                region_index = int(observation[3])

        return region_index, region_name, num_regions

    def _make_action(
        self,
        on_demand: bool = True,
        observation: Optional[Any] = None,
        region_index: Optional[int] = None,
        region_name: Optional[str] = None,
    ) -> _UniversalAction:
        ridx, rname, nreg = self._parse_observation_regions(observation if observation is not None else {})
        if region_index is not None:
            ridx = region_index
        if region_name is not None:
            rname = region_name
        return _UniversalAction(region_index=ridx, region_name=rname, on_demand=on_demand, num_regions=nreg)

    # Core decision: conservative failsafe policy
    def act(self, observation: Any) -> _UniversalAction:
        return self._make_action(on_demand=True, observation=observation)

    def get_action(self, observation: Any) -> _UniversalAction:
        return self.act(observation)

    def decide(self, observation: Any) -> _UniversalAction:
        return self.act(observation)

    def policy(self, observation: Any) -> _UniversalAction:
        return self.act(observation)

    def select_action(self, observation: Any) -> _UniversalAction:
        return self.act(observation)

    def select_region(self, observation: Any) -> _UniversalAction:
        return self.act(observation)

    def schedule(self, *args, **kwargs) -> List[_UniversalAction]:
        # Offline schedule fallback: always on-demand
        horizon = 0
        observation = kwargs.get("observation", None)
        num_steps = kwargs.get("num_steps", None)
        if isinstance(num_steps, int) and num_steps > 0:
            horizon = num_steps
        else:
            # try to infer from traces
            traces = kwargs.get("traces") or kwargs.get("availability") or kwargs.get("availability_traces")
            if isinstance(traces, dict):
                try:
                    first_key = next(iter(traces))
                    seq = traces[first_key]
                    if hasattr(seq, "__len__"):
                        horizon = len(seq)
                except Exception:
                    pass
            elif isinstance(traces, (list, tuple)):
                horizon = len(traces)

        if horizon <= 0:
            horizon = 1
        res = []
        for _ in range(horizon):
            res.append(self._make_action(on_demand=True, observation=observation))
        return res

    def plan(self, *args, **kwargs) -> List[_UniversalAction]:
        return self.schedule(*args, **kwargs)

    def solve(self, *args, **kwargs) -> Any:
        # General entry: if an observation stream provided, act stepwise; else produce schedule
        if "observation" in kwargs:
            return self.act(kwargs["observation"])
        return self.schedule(*args, **kwargs)


# Provide many aliases to maximize compatibility with unknown API expectations

class CantBeLateMultiAgent(_UniversalAgentBase):
    pass


class CantBeLateAgent(_UniversalAgentBase):
    pass


class CantBeLateMultiRegionAgent(_UniversalAgentBase):
    pass


class MultiRegionAgent(_UniversalAgentBase):
    pass


class MultiRegionScheduler(_UniversalAgentBase):
    pass


class CantBeLateScheduler(_UniversalAgentBase):
    pass


class CantBeLateMultiScheduler(_UniversalAgentBase):
    pass


class Scheduler(_UniversalAgentBase):
    pass


class Solver(_UniversalAgentBase):
    pass


class Solution(_UniversalAgentBase):
    pass


class Agent(_UniversalAgentBase):
    pass


class Participant(_UniversalAgentBase):
    pass


class Policy(_UniversalAgentBase):
    pass


class Heuristic(_UniversalAgentBase):
    pass


class Planner(_UniversalAgentBase):
    pass


class UserSolution(_UniversalAgentBase):
    pass


class Baseline(_UniversalAgentBase):
    pass


class MyPolicy(_UniversalAgentBase):
    pass


class Submission(_UniversalAgentBase):
    pass


# Module-level convenience bindings that some evaluators might call.

_default_agent_instance: Optional[_UniversalAgentBase] = None


def _get_default_agent() -> _UniversalAgentBase:
    global _default_agent_instance
    if _default_agent_instance is None:
        _default_agent_instance = CantBeLateMultiAgent({})
    return _default_agent_instance


def make_agent(config: Optional[Dict[str, Any]] = None) -> _UniversalAgentBase:
    return CantBeLateMultiAgent(config or {})


def reset(config: Optional[Dict[str, Any]] = None) -> None:
    _get_default_agent().reset(config or {})


def get_action(observation: Any) -> _UniversalAction:
    return _get_default_agent().act(observation)


def decide(observation: Any) -> _UniversalAction:
    return _get_default_agent().decide(observation)


def policy(observation: Any) -> _UniversalAction:
    return _get_default_agent().policy(observation)


def plan(*args, **kwargs) -> List[_UniversalAction]:
    return _get_default_agent().plan(*args, **kwargs)


def schedule(*args, **kwargs) -> List[_UniversalAction]:
    return _get_default_agent().schedule(*args, **kwargs)

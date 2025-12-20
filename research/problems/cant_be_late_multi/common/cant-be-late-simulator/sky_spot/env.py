import math
import json
import logging
import os
import typing
from typing import Dict, List, Tuple, Type, Sequence, Optional
import abc

from sky_spot import trace
from sky_spot.utils import ClusterType, COSTS, DEVICE_COSTS, COST_K
from sky_spot import task as task_lib

if typing.TYPE_CHECKING:
    import configargparse

logger = logging.getLogger(__name__)


class RegionAwareEnv(abc.ABC):
    """Unified interface for environments that support region operations."""
    
    def get_num_regions(self) -> int:
        """Return the number of available regions. Single-region environments return 1."""
        return 1
    
    def get_current_region(self) -> int:
        """Return the currently active region index. Single-region environments return 0."""
        return 0
    
    def switch_region(self, region_idx: int) -> bool:
        """Switch to the specified region. Returns True if successful."""
        return True  # Single-region env: no-op, always success
    
    def get_all_regions_spot_available(self) -> List[bool]:
        """Return spot availability for all regions."""
        return [self.spot_available()]  # This method should exist in concrete env classes
    
    def spot_available_in_region(self, region_idx: int) -> bool:
        """Check spot availability in a specific region."""
        assert 0 <= region_idx < self.get_num_regions(), f"Region {region_idx} out of range"
        if region_idx == self.get_current_region():
            return self.spot_available()
        else:
            return False  # For single-region envs, only current region is valid


class Env(RegionAwareEnv):
    NAME = 'abstract'
    SUBCLASSES: Dict[str, Type['Env']] = {}

    def __init__(self, gap_seconds: float):
        self.gap_seconds = gap_seconds
        self.reset()

    def reset(self):
        # dones not include the cluster_type for the current timestamp - 1 -> timestamp, until observed on timestamp
        self.cluster_type_histroy = []
        self.cluster_type = ClusterType.NONE
        self.tick = 0
        self.observed_tick = -1

    def __init_subclass__(cls) -> None:
        assert cls.NAME not in cls.SUBCLASSES and cls.NAME != 'abstract', f'Name {cls.NAME} already exists'
        cls.SUBCLASSES[cls.NAME] = cls

    def spot_available(self) -> bool:
        """
        Returns True if spot is available at the current timestamp -> timestamp + 1
        """
        raise NotImplementedError

    def observe(self) -> Tuple[ClusterType, bool]:
        """
        Returns the cluster type (at last time gap) and whether spot is available
        """
        assert self.observed_tick == self.tick - 1, (self.observed_tick,
                                                     self.tick)
        self.observed_tick = self.tick
        has_spot = self.spot_available()
        last_cluster_type = self.cluster_type
        self.cluster_type_histroy.append(last_cluster_type)

        if self.cluster_type == ClusterType.SPOT and not has_spot:
            logger.debug(f'Preempted at {self.tick}')
            self.cluster_type = ClusterType.NONE
        return last_cluster_type, has_spot

    def step(self, request_type: ClusterType):
        if self.observed_tick != self.tick:
            self.observe()
        if request_type == ClusterType.SPOT and not self.spot_available():
            raise ValueError('Spot not available')
        new_cluster_type = self._step(request_type)
        self.tick += 1
        return new_cluster_type

    def _step(self, request_type: ClusterType):
        self.cluster_type = request_type
        return self.cluster_type

    def get_trace_before_end(self, end: float) -> trace.Trace:
        # Used for ideal strategy
        raise NotImplementedError

    @property
    def elapsed_seconds(self) -> float:
        return self.tick * self.gap_seconds

    @property
    def accumulated_cost(self) -> float:
        """Accumulated cost of the environment"""
        costs_map = self.get_constant_cost_map()
        return sum(costs_map[cluster_type] * self.gap_seconds / 3600
                   for cluster_type in self.cluster_type_histroy)

    def get_constant_cost_map(self) -> Dict[ClusterType, float]:
        return COSTS

    def info(self) -> dict:
        # Step should have been called
        assert self.tick == self.observed_tick + 1
        return {
            'Timestamp':
            self.tick - 1,
            'Elapsed': (self.tick - 1) * self.gap_seconds,
            'Cost':
            self.accumulated_cost,
            'ClusterType':
            self.cluster_type_histroy[-1].value
            if self.cluster_type_histroy else ClusterType.NONE.value,
        }

    def __repr__(self) -> str:
        return f'{self.NAME}({json.dumps(self.config)})'

    @property
    def config(self):
        return dict()

    @classmethod
    def from_args(cls,
                  parser: 'configargparse.ArgumentParser') -> Sequence['Env']:
        # parser.add_argument(f'--env-config', type=str, default=None, is_config_file=True, required=False)
        parser.add_argument('--env',
                            type=str,
                            default='trace',
                            choices=cls.SUBCLASSES.keys())
        args, _ = parser.parse_known_args()
        cls = cls.SUBCLASSES[args.env]
        return cls._from_args(parser)

    @classmethod
    def _from_args(cls,
                   parser: 'configargparse.ArgumentParser') -> Sequence['Env']:
        raise NotImplementedError


class TraceEnv(Env):
    NAME = 'trace'

    def __init__(self, trace_file: str, env_start_hours: float):

        self._trace_file = trace_file
        self.trace: trace.Trace = trace.Trace.from_file(trace_file)

        self._start_index = 0
        if env_start_hours > 0:
            self._start_index = int(
                math.ceil(env_start_hours * 3600 / self.trace.gap_seconds))

        for device, cost in DEVICE_COSTS.items():
            if device in trace_file:
                self._base_price = cost
                break
        assert self._base_price is not None, f'No base price found for {trace_file}'

        self._spot_price = None
        if self.trace.get_price(0) is None:
            self._spot_price = self._base_price / COST_K

        super().__init__(self.trace.gap_seconds)

    def spot_available(self) -> bool:
        tick = self.tick + self._start_index
        if tick >= len(self.trace):
            raise ValueError(
                f'Timestamp {tick} out of range {len(self.trace)}')
        return not self.trace[tick]

    def get_trace_before_end(self, end: float) -> trace.Trace:
        end_index = int(math.ceil(end / self.gap_seconds))
        return self.trace[self._start_index:end_index + self._start_index]

    def next_wait_spot_length(self) -> Tuple[int, int]:
        wait_length = 0
        spot_length = 0
        start = self.tick + self._start_index
        if not self.spot_available():
            for i in range(start, len(self.trace)):
                if not self.trace[i]:
                    start = i
                    break
                wait_length += 1

        for i in range(start, len(self.trace)):
            if not self.trace[i]:
                spot_length += 1
            else:
                break
        return wait_length, spot_length

    def get_constant_cost_map(self) -> Dict[ClusterType, float]:
        return {
            ClusterType.ON_DEMAND:
            float(self._base_price),
            ClusterType.SPOT:
            float(self.trace.get_price(0))
            if self._spot_price is None else float(self._spot_price),
            ClusterType.NONE:
            0.0,
        }

    def get_price(self) -> Dict[ClusterType, float]:
        if self._spot_price is not None:
            return {
                ClusterType.ON_DEMAND: float(self._base_price),
                ClusterType.SPOT: float(self._spot_price),
                ClusterType.NONE: 0.0,
            }
        spot_price = self.trace.get_price(self.tick + self._start_index)
        assert spot_price is not None, 'Spot price not available'
        return {
            ClusterType.ON_DEMAND: float(self._base_price),
            ClusterType.SPOT: spot_price,
            ClusterType.NONE: 0.0,
        }

    @property
    def config(self) -> dict:
        return {
            'name': self.NAME,
            'trace_file': self._trace_file,
            'start_index': self._start_index,
            'metadata': self.trace.metadata,
            'tace_file': self._trace_file
        }

    @classmethod
    def _from_args(
            cls,
            parser: 'configargparse.ArgumentParser') -> Sequence['TraceEnv']:
        group = parser.add_argument_group('TraceEnv')
        group.add_argument('--trace-file',
                           type=str,
                           help='File/folder containing the trace')
        group.add_argument('--env-start-hours',
                           type=float,
                           default=0,
                           help='Start hours of the trace')
        args, _ = parser.parse_known_args()
        return cls.create_env(args.trace_file, args.env_start_hours)

    @classmethod
    def create_env(cls, trace_file_or_dir: str,
                   env_start_hours: float) -> Sequence['TraceEnv']:
        if os.path.isdir(trace_file_or_dir):
            trace_files = []
            for file in sorted(os.listdir(trace_file_or_dir),
                               key=lambda x: int(x.split('.')[0])):
                # logger.debug(file)
                if file.endswith('.json'):
                    trace_files.append(os.path.join(trace_file_or_dir, file))
            return [
                cls(trace_file, env_start_hours) for trace_file in trace_files
            ]
        return [cls(trace_file_or_dir, env_start_hours)]


class MultiTraceEnv(Env):
    NAME = 'multi_trace'

    def __init__(self, trace_files: List[str], env_start_hours: float):
        self._trace_files = trace_files
        self.envs = [
            TraceEnv(trace_file, env_start_hours) for trace_file in trace_files
        ]
        self.num_regions = len(trace_files)

        gap_seconds = self.envs[0].trace.gap_seconds
        for env in self.envs:
            assert env.trace.gap_seconds == gap_seconds, "All traces must have the same gap seconds"

        self.max_ticks = min(
            len(env.trace) - env._start_index for env in self.envs)

        self.current_region = 0  # Start with the first region

        super().__init__(gap_seconds)
        logger.debug(
            f"MultiTraceEnv initialized with {self.num_regions} regions: {trace_files}"
        )
        logger.debug(f"Maximum available ticks: {self.max_ticks}")

    def reset(self):
        super().reset()
        for env in self.envs:
            env.reset()
        self.current_region = 0
        logger.debug("MultiTraceEnv reset completed")

    def spot_available(self) -> bool:
        return self.spot_available_in_region(self.current_region)

    def spot_available_in_region(self, region_idx: int) -> bool:
        """Check spot availability in a specific region."""
        assert 0 <= region_idx < self.num_regions, f'Region index {region_idx} out of range'
        # CRITICAL: Sync the tick of the region with the switcher's tick
        self.envs[region_idx].tick = self.tick
        return self.envs[region_idx].spot_available()

    def get_all_regions_spot_available(self) -> List[bool]:
        """Return spot availability for all regions."""
        return [
            self.spot_available_in_region(i) for i in range(self.num_regions)
        ]

    def get_all_regions_spot_prices(self) -> List[Optional[float]]:
        """Return spot prices for all regions. If a region's spot is not available, its price is None."""
        prices = []
        for i in range(self.num_regions):
            # Sync tick before getting any info from sub-env
            self.envs[i].tick = self.tick
            if self.envs[i].spot_available():
                price_map = self.envs[i].get_price()
                prices.append(price_map.get(ClusterType.SPOT))
            else:
                prices.append(None)
        return prices

    def get_all_regions_ondemand_prices(self) -> List[float]:
        """Return on-demand prices for all regions."""
        prices = []
        for i in range(self.num_regions):
            price_map = self.envs[i].get_constant_cost_map()
            prices.append(price_map[ClusterType.ON_DEMAND])
        return prices

    def observe(self) -> Tuple[ClusterType, bool]:
        assert self.observed_tick == self.tick - 1, (self.observed_tick,
                                                     self.tick)
        self.observed_tick = self.tick
        has_spot = self.spot_available()
        last_cluster_type = self.cluster_type
        self.cluster_type_histroy.append(last_cluster_type)

        if self.cluster_type == ClusterType.SPOT and not has_spot:
            logger.debug(
                f'Preempted at {self.tick} in region {self.current_region}')
            self.cluster_type = ClusterType.NONE
        return last_cluster_type, has_spot

    def get_trace_before_end(self, end: float) -> trace.Trace:
        return self.envs[self.current_region].get_trace_before_end(end)

    def switch_region(self, region_idx: int) -> bool:
        """Switch to the specified region."""
        assert 0 <= region_idx < self.num_regions, f'Region index {region_idx} out of range'
        
        old_region = self.current_region
        self.current_region = region_idx
        logger.debug(f"Switched from region {old_region} to region {region_idx}")
        return True

    def get_current_region(self) -> int:
        """Return the currently active region index."""
        return self.current_region

    def get_num_regions(self) -> int:
        """Return the number of available regions."""
        return self.num_regions

    def get_constant_cost_map(self) -> Dict[ClusterType, float]:
        return self.envs[self.current_region].get_constant_cost_map()

    def get_price(self) -> Dict[ClusterType, float]:
        return self.envs[self.current_region].get_price()

    @property
    def config(self) -> dict:
        return {
            'name': self.NAME,
            'trace_files': self._trace_files,
            'num_regions': self.num_regions,
            'metadata': [env.trace.metadata for env in self.envs]
        }

    @classmethod
    def _from_args(
            cls, parser: 'configargparse.ArgumentParser'
    ) -> Sequence['MultiTraceEnv']:
        group = parser.add_argument_group('MultiTraceEnv')
        group.add_argument(
            '--trace-files',
            type=str,
            nargs='+',
            help='Files/folders containing the traces for different regions')
        group.add_argument('--env-start-hours',
                           type=float,
                           default=0,
                           help='Start hours of the trace')
        args, _ = parser.parse_known_args()
        assert hasattr(args, 'trace_files') and args.trace_files, "No trace-files provided for MultiTraceEnv"
        return cls.create_env(args.trace_files, args.env_start_hours)
    
    @classmethod
    def create_env(cls, trace_files_or_dirs: List[str], env_start_hours: float) -> List['MultiTraceEnv']:
        """Create MultiTraceEnv instances using corresponding indexed files from each region."""
        
        # Step 1: Collect all trace files by region
        region_files = []
        for path in trace_files_or_dirs:
            if os.path.isdir(path):
                files = sorted([
                    os.path.join(path, f) for f in os.listdir(path) 
                    if f.endswith('.json')
                ], key=lambda x: int(os.path.basename(x).split('.')[0]))
                region_files.append(files)
            else:
                region_files.append([path])
        
        # Step 2: Create one MultiTraceEnv per common index
        min_traces = min(len(files) for files in region_files)
        return [
            cls([region_files[region_idx][i] for region_idx in range(len(region_files))], env_start_hours)
            for i in range(min_traces)
        ]

class SubtaskMultiEnvSwitcher(Env):
    """An Env wrapper that switches between underlying MultiTraceEnvs 
    base on the progress of a ChainedTask."""
    NAME = 'subtask_multi_env_switcher'

    def __init__(self, sub_environments: List[MultiTraceEnv]):
        """Initialize the switcher with pre-created sub-environments.

        Args:
            sub_environments: A list of already instantiated MultiTraceEnv objects.
        """
        if not sub_environments:
            raise ValueError("sub_environments cannot be empty.")

        self.sub_environments = sub_environments
        first_gap_seconds = self.sub_environments[0].gap_seconds

        # Verify gap_seconds consistency
        for i, sub_env in enumerate(self.sub_environments):
            if sub_env.gap_seconds != first_gap_seconds:
                raise ValueError(f"Sub-environment at index {i} has mismatching gap_seconds.")

        self.task: Optional[task_lib.ChainedTask] = None
        # Store config differently or reconstruct if needed for the config property
        # Let's store the configs from the passed instances for now
        self._sub_task_env_configs = [sub_env.config for sub_env in self.sub_environments]
        # Default start hours is less relevant now, maybe store the first one?
        self._default_env_start_hours = getattr(self.sub_environments[0], '_start_index', 0) * first_gap_seconds / 3600.0 

        super().__init__(first_gap_seconds)
        logger.debug(f"SubtaskMultiEnvSwitcher initialized with {len(self.sub_environments)} sub-environments.")

    def set_task(self, task: 'task_lib.ChainedTask'):
        """Set the ChainedTask instance to track progress."""
        if not isinstance(task, task_lib.ChainedTask):
            raise TypeError("Task must be an instance of ChainedTask for SubtaskMultiEnvSwitcher.")
        if len(task._sub_tasks) != len(self.sub_environments):
            raise ValueError("Number of sub-tasks in ChainedTask must match the number of sub-environments.")
        self.task = task
        logger.debug(f"ChainedTask set for SubtaskMultiEnvSwitcher.")

    def _get_current_sub_env(self) -> MultiTraceEnv:
        """Get the MultiTraceEnv corresponding to the current sub-task."""
        if self.task is None:
            raise RuntimeError("Task has not been set using set_task().")
        
        current_index = self.task.get_current_subtask_index()
        if not (0 <= current_index < len(self.sub_environments)):
            raise IndexError(f"Current sub-task index {current_index} is out of bounds for sub-environments.")
        
        # Sync the tick of the sub-env with the switcher's tick
        sub_env = self.sub_environments[current_index]
        sub_env.tick = self.tick 
        return sub_env

    def reset(self):
        super().reset()
        # Reset all sub-environments as well
        for sub_env in self.sub_environments:
            sub_env.reset()
        self.task = None
        logger.debug("SubtaskMultiEnvSwitcher reset completed.")

    # --- RegionAwareEnv interface implementation ---
    def get_num_regions(self) -> int:
        """Return the number of regions from the current sub-environment."""
        return self._get_current_sub_env().get_num_regions()

    def get_current_region(self) -> int:
        """Return the current region from the current sub-environment."""
        return self._get_current_sub_env().get_current_region()

    def switch_region(self, region_idx: int) -> bool:
        """Switch region in the current sub-environment."""
        success = self._get_current_sub_env().switch_region(region_idx)
        if success:
            logger.debug(f"Switcher delegated switch_region({region_idx}) to sub-env {self.task.get_current_subtask_index() if self.task else -1}")
        return success
        
    def spot_available_in_region(self, region_idx: int) -> bool:
        """Check spot availability in the specified region of the current sub-environment."""
        return self._get_current_sub_env().spot_available_in_region(region_idx)

    def get_all_regions_spot_available(self) -> List[bool]:
        """Return spot availability for all regions in the current sub-environment."""
        return self._get_current_sub_env().get_all_regions_spot_available()

    def spot_available(self) -> bool:
        """Check spot availability in the current sub-environment."""
        current_sub_env = self._get_current_sub_env()
        # Sync cluster type to ensure consistency
        current_sub_env.cluster_type = self.cluster_type 
        return current_sub_env.spot_available()

    def observe(self) -> Tuple[ClusterType, bool]:
        """Observe state through the current sub-environment."""
        if self.task is None:
            raise RuntimeError("Task not set")
        
        # Check switcher's consistency
        assert self.observed_tick == self.tick - 1, (f"Switcher state inconsistency: observed={self.observed_tick}, tick={self.tick}")
        self.observed_tick = self.tick

        # Get current sub-environment and sync state
        current_sub_env = self._get_current_sub_env() 
        current_sub_env.cluster_type = self.cluster_type
        has_spot = current_sub_env.spot_available() 

        # Record previous state in switcher's history
        last_switcher_cluster_type = self.cluster_type
        self.cluster_type_histroy.append(last_switcher_cluster_type)

        # Update state based on preemption
        if self.cluster_type == ClusterType.SPOT and not has_spot:
            logger.debug(f'Switcher observed preemption via sub-env {self.task.get_current_subtask_index()} at tick {self.tick}')
            self.cluster_type = ClusterType.NONE
            current_sub_env.cluster_type = ClusterType.NONE 

        return last_switcher_cluster_type, has_spot

    def step(self, request_type: ClusterType):
        """Step the switcher and sync with current sub-environment."""
        if self.observed_tick != self.tick:
            self.observe() 
        
        current_sub_env = self._get_current_sub_env() 
        
        # Update switcher's cluster type
        new_cluster_type = self._step(request_type)
        self.tick += 1 
        
        # Sync state to current sub-environment
        current_sub_env.cluster_type = new_cluster_type
        
        return new_cluster_type

    def get_constant_cost_map(self) -> Dict[ClusterType, float]:
        """Get cost map from the current sub-environment."""
        current_sub_env = self._get_current_sub_env()
        return current_sub_env.get_constant_cost_map()

    def get_price(self) -> Dict[ClusterType, float]:
        """Get price from the current sub-environment."""
        current_sub_env = self._get_current_sub_env()
        return current_sub_env.get_price()

    def info(self) -> dict:
        """Return info combining switcher state with current sub-environment details."""
        base_info = super().info()
        try:
            current_index = self.task.get_current_subtask_index() if self.task else -1
            base_info['current_sub_env_index'] = current_index
        except Exception as e:
            logger.warning(f"Could not get sub-env info: {e}") 
            base_info['current_sub_env_index'] = -1
        return base_info

    @property
    def config(self):
        return {
            'name': self.NAME,
            'sub_task_env_configs': self._sub_task_env_configs,
            'default_env_start_hours': self._default_env_start_hours,
            'gap_seconds': self.gap_seconds 
        }

    @classmethod
    def _from_args(
            cls,
            parser: 'configargparse.ArgumentParser') -> Sequence['SubtaskMultiEnvSwitcher']:
        # For now, assume this Env is primarily created via YAML config in main.py
        raise NotImplementedError(f"{cls.NAME} cannot be created directly using from_args yet.")
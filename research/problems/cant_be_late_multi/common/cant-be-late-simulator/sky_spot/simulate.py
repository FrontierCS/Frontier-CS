import json
import logging
import os
from typing import Sequence, Optional

import tqdm
import wandb
import numpy as np

from sky_spot import env as env_lib
from sky_spot.env import SubtaskMultiEnvSwitcher
from sky_spot.strategies import strategy as strategy_lib
from sky_spot.utils import ClusterType, wandb_log
from sky_spot import task as task_lib

logger = logging.getLogger(__name__)


def _simulate_one(env: env_lib.Env, strategy: strategy_lib.Strategy):
    history = []
    last_request_type = ClusterType.NONE
    while not strategy.task_done:
        request_type = strategy.step()
        env.step(request_type)
        info = {
            "RequestType": last_request_type.value,
            **env.info(),
            **strategy.info(),
        }
        last_request_type = request_type
        history.append(info)
        wandb_log(info)
        if env.tick % 100 == 0:
            logger.debug(f"==> Timestamp: {env.tick}")

    strategy.step()  # realize the last step
    env.step(ClusterType.NONE)
    info = {
        "RequestType": ClusterType.NONE,
        **env.info(),
        **strategy.info(),
    }
    return history, env.tick


def simulate(
    envs: Sequence[env_lib.Env],
    strategy: strategy_lib.Strategy,
    task: task_lib.Task,
    trace_file: str,
    deadline_hours: float,
    restart_overhead_hours: list[float],
    env_start_hours: float,
    output_dir: str,
    kwargs: dict,
    output_filename: Optional[str] = None,
    silent: bool = False,
    dump_history: bool = True,
):
    histories = []
    costs = []
    ticks = []

    trace_file = trace_file.split("/")[-1]
    env_name = envs[0].NAME
    env_config = envs[0].config
    # RESETTING STRATEGY IS VERY IMPORTANT!
    strategy.reset(envs[0], task)

    restart_overhead_str = "_".join(map(str, restart_overhead_hours))
    run_name = f"{strategy.name}-{env_name}-{trace_file}-ddl={deadline_hours}-task={task}-over={restart_overhead_str}"
    if env_start_hours > 0:
        run_name += f"-start={env_start_hours}h"
    logger.debug(run_name)
    if not silent and wandb.run is not None:
        wandb.run.name = run_name
        wandb.config.update(
            {
                "trace_file": trace_file,
                "deadline_hours": deadline_hours,
                "restart_overhead_hours": restart_overhead_hours,
                "env_start_hours": env_start_hours,
                "task_config": task.get_config(),
                "other_args": {
                    k: v
                    for k, v in kwargs.items()
                    if k
                    not in [
                        "deadline_hours",
                        "task_duration_hours",
                        "task_duration_hours_2",
                        "restart_overhead_hours",
                        "env_start_hours",
                    ]
                },
            }
        )
        wandb.config.update({"env_metadata": env_config})
        wandb.config.update({"strategy_metadata": strategy.config})

    if silent:
        pbar = envs
    else:
        pbar = tqdm.tqdm(envs)
    for env in pbar:
        # pbar.set_description(f'env: {env}')
        # ! Must reset env and strategy at the first time!
        # ! reset is their init method
        env.reset()
        strategy.reset(env, task)

        if isinstance(env, SubtaskMultiEnvSwitcher):
            if isinstance(task, task_lib.ChainedTask):
                env.set_task(task)
                logger.debug("Associated ChainedTask with SubtaskMultiEnvSwitcher.")
            else:
                raise ValueError(
                    "SubtaskMultiEnvSwitcher requires a ChainedTask, but received a different task type."
                )

        logger.debug(kwargs)
        logger.debug(env)
        logger.debug(strategy)

        history, tick = _simulate_one(env, strategy)
        histories.append(history)
        costs.append(history[-1]["Cost"])
        ticks.append(tick)

        # if len(envs) > 1:
        #     env.reset()
        #     new_args = copy.deepcopy(args)
        #     new_args.deadline_hours = 1000
        #     spot_strategy = sky_spot.strategies.only_spot.OnlySpotStrategy(new_args)
        #     spot_costs.append(simulate(env, spot_strategy))
        #     cost_ratio.append(costs[-1] / spot_costs[-1])

        # mean_strategy_cost = np.mean(costs)
        # std_strategy_cost = np.std(costs)
        # mean_spot_cost = np.mean(spot_costs)
        # std_spot_cost = np.std(spot_costs)
        # mean_cost_ratio = np.mean(cost_ratio)
        # std_cost_ratio = np.std(cost_ratio)
        # msg = f'cost: {mean_strategy_cost:.2f}±{std_strategy_cost:.2f}; spot cost: {mean_spot_cost:.2f}±{std_spot_cost:.2f}; cost ratio: {mean_cost_ratio:.2f}±{std_cost_ratio:.2f}'
        # logger.debug('=== ' + msg + ' ===')
        # pbar.set_description(msg)
        # wandb.log({'MeanCost': mean_strategy_cost, 'StdCost': std_strategy_cost, 'MeanSpotCost': mean_spot_cost, 'StdSpotCost': std_spot_cost, 'MeanCostRatio': mean_cost_ratio, 'StdCostRatio': std_cost_ratio})

    os.makedirs(output_dir, exist_ok=True)
    if output_filename is not None:
        run_name = output_filename
    stats = {
        "args": kwargs,
        "costs": costs,
        "strategy": strategy.config,
        "env": env_config,
        "task": task.get_config(),
    }
    if dump_history:
        stats.update(
            {
                "history": histories,
                "ticks": ticks,
            }
        )
    with open(f"{output_dir}/{run_name}", "w", encoding="utf-8") as f:
        json.dump(stats, f)
    mean_cost = np.mean(costs)
    std_cost = np.std(costs)
    p99_cost = np.percentile(costs, 99)
    p90_cost = np.percentile(costs, 90)
    logger.info(
        f"mean: {mean_cost}; std: {std_cost}; worst 1%: {p99_cost}; worst 10%: {p90_cost}"
    )
    return stats

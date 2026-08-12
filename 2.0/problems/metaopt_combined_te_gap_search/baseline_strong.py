"""Calibration-only higher-effort solve of the joint MetaOpt formulation."""
from __future__ import annotations

import reference


def search(instance, evaluate_gap):
    original_time_limit = reference.GLOBAL_TIME_LIMIT_SECONDS
    original_work_limit = reference.GLOBAL_WORK_LIMIT
    try:
        reference.GLOBAL_TIME_LIMIT_SECONDS = 25.0
        reference.GLOBAL_WORK_LIMIT = 24.0
        answer = reference._joint_metaopt(instance)
        evaluate_gap(answer)
        return answer
    finally:
        reference.GLOBAL_TIME_LIMIT_SECONDS = original_time_limit
        reference.GLOBAL_WORK_LIMIT = original_work_limit

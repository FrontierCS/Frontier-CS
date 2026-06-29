"""Reference placeholder for the vllm_llm_serving_optimization task.

The Harbor task submits ``/app/solution.patch`` (a Python-only patch against a
clean upstream vLLM v0.11.0 checkout). This Python file exists only so the
Frontier-CS 2.0 task layout stays conventional (cf. nanowm_rollout_speedup); the
actual reference solution lives in ``reference.patch``.

The reference ports the soul of the *continuum* scheduler — **job-level FCFS** —
plus a long-prefill admission cap, entirely server-side and Python-only:

* ``vllm/v1/core/sched/request_queue.py``: a ``JobFCFSRequestQueue`` that orders
  the WAITING queue by each conversation's (``job_id``) first-arrival time, so a
  later turn of an in-flight conversation is admitted ahead of a brand-new job's
  first prefill (and its prefix is already cache-hot). ``job_id`` is read from
  ``request.sampling_params.extra_args`` — the workload sends it via
  ``vllm_xargs`` (vanilla vLLM ignores it); requests without one fall back to
  plain FCFS.
* ``vllm/v1/core/sched/scheduler.py``: caps fresh uncached long prefills per
  step so a burst of new long prompts cannot head-of-line-block decode.

Both change only admission *order* (deterministic, using ``arrival_time``, never
wall-clock), so generated tokens at temperature 0 are unchanged and the greedy /
BFCL correctness gates pass. See DESIGN.md.
"""

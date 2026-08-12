"""Locked training/eval harness for nanoslm_hybrid_arch_design.

Only ``model.py`` is submitted by the agent; everything in this package is
judge-owned and not part of the submission. The torch-free modules
(:mod:`settings`, :mod:`policy`, :mod:`scoring`) are unit-testable on CPU with
no GPU or PyTorch (as is :mod:`model_config`); the torch-dependent modules
(:mod:`data`, :mod:`train`,
:mod:`eval_ppl`, :mod:`baseline_model`, :mod:`runner`) run on the H100.
"""

"""ModelConfig: the read-only contract object passed to the agent's factory.

Torch-free. The agent's ``build_model(config)`` / ``NanoSLM(config)`` receives one
of these. ``vocab_size`` is fixed by the judge; the agent chooses internal
width/depth/etc. freely inside the model. The ``*_hint`` fields are
informational (so a model can size itself to the budget) and carry no
guarantees.

TWO CONTEXT LENGTHS
-------------------
``block_size``      the context this model will be TRAINED at. It is the judge's
                    default (8192) unless model.py declares a module-level
                    ``BLOCK_SIZE``, in which case it is that value.
``eval_block_size`` the context it will be SCORED at. ALWAYS 8192, whatever the
                    training context is.

When those differ the model is asked for logits at positions it never saw during
training, so anything sized or cached off ``block_size`` (RoPE tables,
positional embeddings, mask buffers) must still work at ``eval_block_size`` --
build such buffers against ``eval_block_size``, or lazily against the actual
``T``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int
    block_size: int              # TRAINING context (per-submission)
    eval_block_size: int = 8192  # SCORING context (fixed by the judge)
    # Read-only budget hints (informational; not part of the scored contract).
    train_seconds_hint: float = 0.0
    param_cap_hint: int = 0
    device_hint: str = "cuda"

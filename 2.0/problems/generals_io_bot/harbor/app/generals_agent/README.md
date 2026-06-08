# Generals Agent Skeleton

Edit `bot.py` and implement `FrontierAgent`.

The judge-side arena is black-box. This workspace contains the bot skeleton and
the public `generals-bots` package, but no Frontier-CS evaluation harness,
baseline ensemble, seeds, or match runner.

Useful imports:

```python
import jax.numpy as jnp
from generals.core.action import create_action, compute_valid_move_mask_obs
from generals.agents import Agent
```

Action format:

```text
[pass, row, col, direction, split]
```

Directions:

```text
0 up, 1 down, 2 left, 3 right
```

Create a patch submission:

```bash
bash /app/make_submission.sh
bash /app/submit.sh
```

Submit the baseline skeleton once before running long local experiments, then
submit every meaningful improvement. Local simulations are useful only for tiny
sanity checks; the black-box judge is the scoring feedback for this task, and
submissions run asynchronously while you keep improving.

The judge accepts patches touching only `bot.py`, `strategy.py`, and `utils.py`.
Do not read files, launch subprocesses, open network sockets, or inspect
environment variables; the evaluator rejects these patterns.

The simulator is JAX-based. Compact array logic usually runs faster than large
Python-heavy policies.

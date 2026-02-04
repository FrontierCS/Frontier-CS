# Evaluating Your Model

> **For Model Providers**: Complete workflow for benchmarking your model on Frontier-CS and submitting results to the leaderboard.

## Step 1: Prepare Solutions

Place your solutions in the correct directory structure:

```
{track}/solutions/{problem}/{model}.{ext}
{track}/solutions/{problem}/{model}_{variant}.{ext}
```

**Examples:**
```
research/solutions/flash_attn/my_model.py
research/solutions/flash_attn/my_model_1.py      # variant 1
research/solutions/gemm_optimization/squares/my_model.py
algorithmic/solutions/1/my_model.cpp
```

- **Research track**: Python (`.py`) by default, or C++ (`.cpp`) if problem specifies `language: cpp` in config.yaml
- **Algorithmic track**: C++17 (`.cpp`)
- We recommend generating **5 variants per model** to compute Score@5

## Step 2: Run Evaluation

Suppose you have a new model `my_model` and want to evaluate it. Three ways:

**1. Put solutions in `solutions/` directory**

```
research/solutions/
├── flash_attn/my_model.py
├── cross_entropy/my_model.py
└── ...
```
```bash
frontier batch research --model my_model
```

**2. Use your own directory**

```
./my_solutions/
├── flash_attn/my_model.py
├── cross_entropy/my_model.py
└── ...
```
```bash
frontier batch research --solutions-dir ./my_solutions
```

**3. Explicit pairs file**

```
# pairs.txt
./my_solutions/flash_attn/my_model.py:flash_attn
./my_solutions/cross_entropy/my_model.py:cross_entropy
```
```bash
frontier batch research --pairs-file pairs.txt
```

### Backend Options

```bash
# Research defaults to SkyPilot, algorithmic defaults to Docker
frontier batch research --backend docker
frontier batch algorithmic --backend skypilot

# Parallelism
frontier batch research --workers 20 --clusters 4
```

### Result Storage

```bash
# Local (default): results saved to ./results/batch/{track}/
frontier batch research

# Cloud bucket (requires --backend skypilot): results written directly to S3/GCS
frontier batch research --bucket-url s3://my-bucket/results

# Sync from bucket to local
frontier batch research --bucket-url s3://my-bucket/results --sync-bucket
```

### Control Options

```bash
frontier batch research --status          # Check status
frontier batch research --no-resume       # Force re-evaluate all
frontier batch research --retry-failed    # Retry failed (including score=0)
```

- Incremental evaluation with hash-based caching (solution/problem changes trigger re-evaluation)

## Step 3: View Results

Results from public test case evaluation are saved to `./results/batch/{track}/`:

| File | Content |
|------|---------|
| `results.csv` | All evaluation results |
| `by_model.csv` | Score@1, Avg@5, Score@5 per model |
| `by_problem.csv` | Scores per problem |
| `failed.txt` | Failed evaluations |
| `pending.txt` | Pending evaluations |

## Step 4: Submit to Leaderboard

We welcome submissions from all models and agent frameworks. To have your results included in our leaderboard, please follow the instructions below.

### Algorithmic Problems

We currently release **1-3 public test cases** per problem for local testing and debugging. Full evaluation (with all test cases) is performed on our servers.

#### What to Submit

1. **Solution files**: `{problem_id}_{model_name}_solution.cpp` for each problem
2. **Model/Agent info**: Name and version of the model or agent framework used
3. **Generation method**: Brief description of how solutions were generated (e.g., one-shot, multi-turn, with/without feedback)

#### Submission Format

Organize your solutions as:
```
submissions/
├── 1_gpt4_solution.cpp
├── 2_gpt4_solution.cpp
├── ...
└── metadata.json
```

`metadata.json`:
```json
{
  "model": "gpt-4o",
  "agent_framework": "custom",
  "generation_method": "one-shot",
  "date": "2025-01-15",
  "notes": "Optional additional notes"
}
```

### Research Problems

Research problems require a `solution.py` file implementing the `Solution` class interface.

#### Problem Structure

Research problems follow a hierarchical structure:

```
Problem (e.g., gemm_optimization, poc_generation)
└── Category (e.g., squares, heap_buffer_overflow)
    └── Variant (e.g., arvo_21000)
```

| Level | Example | Description |
|-------|---------|-------------|
| **Problem** | `gemm_optimization` | Top-level problem domain |
| **Category** | `gemm_optimization/squares` | Scores are **aggregated** at this level for leaderboard reporting |
| **Variant** | `poc_generation/heap_buffer_overflow/arvo_21000` | Each variant is **evaluated independently** with its own README |

**Key distinction:**
- **Evaluation**: Each variant runs independently and produces its own score
- **Reporting**: Scores are aggregated by category for the leaderboard (e.g., all `heap_buffer_overflow` variants → one score)

> Note: Some problems have only one level (e.g., `flash_attn`), which functions as both category and variant.

#### Problem ID Format

Each variant has a unique **Problem ID** based on its path under `research/`.

The full list of all evaluatable variants is in [`research/scripts/problems.txt`](research/scripts/problems.txt).

| Type | Example Path | Problem ID |
|------|-------------|------------|
| Single problem | `research/flash_attn` | `flash_attn` |
| Problem with variants | `research/gemm_optimization/squares` | `gemm_optimization/squares` |
| Nested variants | `research/poc_generation/heap_buffer_overflow/arvo_21000` | `poc_generation/heap_buffer_overflow/arvo_21000` |

#### What to Submit

1. **Solution files**: `solution.py` for each problem, placed in a directory matching the Problem ID
2. **Model/Agent info**: Name and version of the model or agent framework used
3. **Local evaluation results** (optional but recommended): Score from running the evaluator locally

#### Submission Format

Your submission zip should mirror the Problem ID directory structure:

```
submission.zip
├── flash_attn/
│   └── solution.py
├── gemm_optimization/
│   └── squares/
│       └── solution.py
├── cant_be_late/
│   └── high_availability_loose_deadline/
│       └── solution.py
├── poc_generation/
│   └── heap_buffer_overflow/
│       └── arvo_21000/
│           └── solution.py
└── metadata.json
```

**Important**: The directory structure must exactly match the Problem ID. For example:
- `flash_attn/solution.py`
- `gemm_optimization/squares/solution.py`

Each `solution.py` must implement:
```python
class Solution:
    def __init__(self):
        pass

    def solve(self, *args):
        # Returns: solution output (format varies by problem)
        pass
```

#### metadata.json

```json
{
  "model": "gpt-4o",
  "agent_framework": "custom",
  "generation_method": "one-shot",
  "date": "2025-01-15",
  "problems_solved": [
    "flash_attn",
    "gemm_optimization/squares",
    "cant_be_late/high_availability_loose_deadline"
  ],
  "notes": "Optional additional notes"
}
```

### How to Submit

Send your submission to:
- **Email**: qmang@berkeley.edu or wenhao.chai@princeton.edu

Please include:
1. A zip/tar archive of your solutions following the format above
2. `metadata.json` with model and method information
3. (Optional) Local evaluation results if you ran them

### Leaderboard

Accepted submissions will be evaluated on our full test suite and results will be published on the [Frontier-CS Leaderboard](https://frontier-cs.org).

## How We Evaluate Submissions

After you submit, maintainers evaluate your solutions against the full private test suite. This runs automatically via weekly CI or manually by maintainers:

```bash
./scripts/run_eval.sh --track research
./scripts/run_eval.sh --track algorithmic
```

Options:
- `-j N`: Parallelism (default: 10)
- `--force`: Force re-evaluate all
- `--no-push`: Don't push results

Results are saved to `Frontier-CS-Result/` repository and published to the leaderboard.

---

## Using Our Generation Scripts (Optional)

If you want to use our scripts to batch-generate solutions with LLMs:

### Configure

**models.txt** (`research/scripts/models.txt` or `algorithmic/scripts/models.txt`)
- One model name per line
- Supported formats: `gpt-5`, `claude-sonnet-4-5`, `gemini/gemini-2.5-pro`, `xai/grok-4`, `deepseek/deepseek-reasoner`

**indices.txt**
- Controls how many variants to generate per (model, problem) pair
- Single number N = generate indices 0 to N-1
- Multiple lines = specify explicit indices

**API Keys**

Set environment variables for the providers you need. Multiple keys per provider are supported for load balancing (e.g., `OPENAI_API_KEY`, `OPENAI_API_KEY2`, `OPENAI_API_KEY_2`).

| Provider   | Environment Variable | Models                                |
| ---------- | -------------------- | ------------------------------------- |
| OpenAI     | `OPENAI_API_KEY`     | gpt-4o, gpt-5, o1, o3, ...            |
| Anthropic  | `ANTHROPIC_API_KEY`  | claude-sonnet-4-5, claude-opus-4, ... |
| Google     | `GOOGLE_API_KEY`     | gemini-2.5-pro, gemini-2.5-flash, ... |
| xAI        | `XAI_API_KEY`        | grok-3, grok-3-mini, ...              |
| DeepSeek   | `DEEPSEEK_API_KEY`   | deepseek-r1, deepseek-chat, ...       |
| OpenRouter | `OPENROUTER_API_KEY` | openrouter/\* models                  |

```bash
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-...
export GOOGLE_API_KEY=...
```

### Generate Solutions

#### Research Track

Most research problems are Python, but some (e.g., `nbody_simulation`) require C++. The language is configured per-problem via `language` field in `config.yaml`.

```bash
# Generate one solution
python research/scripts/generate_solutions.py --problem flash_attn --model gpt-5 --indices 1

# Preview what would be generated
python research/scripts/generate_solutions.py --dryrun
```

#### Algorithmic Track (C++)

```bash
python algorithmic/scripts/generate_solutions.py --model gpt-5
```

### Two Modes

**Problem mode** (generate new solutions):

```bash
python research/scripts/generate_solutions.py --problem flash_attn --model gpt-5
```

Generates **problems × models × indices** (Cartesian product):

- Problems: `--problem` patterns or `--problems-file` (default: auto-discover all problems)
- Models: `--model` list or `--models-file` (default: `models.txt`)
- Indices: `--indices N` or `--indices-file` (default: `indices.txt` or single solution)

Solution naming: `{problem}/{model}.py` for index 0, `{problem}/{model}_{i}.py` for index i.

**Solution mode** (regenerate existing solutions):

```bash
python research/scripts/generate_solutions.py --solution "flash_attn/gpt5*" --force
```

- Matches existing solutions in `solutions/` by pattern
- Model inferred from solution filename (e.g., `flash_attn/gpt5.py` → model `gpt5`)
- Requires `--force` since solutions already exist
- Still needs `models.txt` or `--model` to map prefix to model name

### Options

| Option                          | Description                                                                    |
| ------------------------------- | ------------------------------------------------------------------------------ |
| `--problem` / `--problems-file` | Problem pattern or file (default: auto-discover)                               |
| `--model` / `--models-file`     | Model(s) or file (default: `models.txt`)                                       |
| `--indices` / `--indices-file`  | Solution indices count or file (default: `indices.txt`)                        |
| `--solution PATTERN`            | Regenerate existing solutions by pattern (mutually exclusive with `--problem`) |
| `--force`                       | Overwrite existing solutions                                                   |
| `--dryrun`                      | Preview without generating                                                     |
| `--concurrency N`               | Parallel API calls                                                             |
| `--timeout SECONDS`             | API timeout (default: 600s)                                                    |

### Output

Solutions are saved in nested directories under `solutions/`:

```
solutions/
├── flash_attn/
│   ├── gpt5.py
│   ├── gpt5_1.py
│   └── claude4.5sonnet.py
└── cross_entropy/
    └── gpt5.py
```

### Check Coverage (Research Only)

```bash
python research/scripts/check_solutions.py
```

Shows:
- **Expected**: models × problems × variants
- **Generated**: expected AND exists
- **Missing**: expected but NOT exists
- **Failed**: `.FAILED` marker files (generation errors)
- **Extra**: exists but NOT expected
- **Empty**: file exists but content is empty

Outputs a coverage progress bar and exports `problems.txt`.

### Customization Points

If you want to modify our scripts:

1. **Use OpenAI-compatible API (e.g., Azure, local models)**
   - Modify `base_url` parameter in `src/frontier_cs/gen/llm.py` `instantiate_llm_client`
   - Or pass `base_url` when initializing `GPT` class in `llm_interface.py`
   - DeepSeek, Grok, etc. are already implemented using OpenAI SDK with different base_url

2. **Add a new LLM provider**
   - Add a new class in `src/frontier_cs/gen/llm_interface.py` (inherit `LLMInterface`, implement `call_llm`)
   - Add provider handling in `src/frontier_cs/gen/llm.py` `instantiate_llm_client`

3. **Add model prefix mapping**
   - Edit `src/frontier_cs/models.py` `get_model_prefix()` to map model name → file prefix
   - Example: `claude-sonnet-4-5-20250929` → `claude4.5sonnet`

4. **Modify prompt templates**
   - Research: system prompt in `research/scripts/generate_solutions.py`
   - Algorithmic: `CPP_SYSTEM_PROMPT` in `algorithmic/scripts/generate_solutions.py`

5. **Customize solution filename format**
   - `src/frontier_cs/gen/solution_format.py`
   - `src/frontier_cs/models.py`: `get_solution_filename()`, `get_solution_path()`

# Algorithmic per-problem scores (updated 2026-10-18)

Scores for the [natural-log scoring rules](../README.md#scoring-principles).
The CSV filenames retain the date of the original 2026-10-17 evaluation.
On 2026-10-18, problems 121 and 133 were rescored from the original per-case
outputs using the corrected floating-point tolerances. No new model attempts
were generated, and the other per-problem scores are unchanged.

| Model / CSV | Reasoning | Problems | Mean score |
|---|---|---:|---:|
| [Opus 5.5](opus-5.5-high-2026-10-17.csv) | high | 179 | 56.52 |
| [GPT-6 Astra](gpt-6-astra-low-2026-10-17.csv) | low | 179 | 53.98 |
| [Sonnet 5.5](sonnet-5.5-max-2026-10-17.csv) | max | 179 | 53.90 |
| [GPT-6 Sol](gpt-6-sol-high-2026-10-17.csv) | high | 179 | 52.38 |
| [Gemini 3.7 Flash](gemini-3.7-flash-medium-2026-10-17.csv) | medium | 179 | 47.97 |
| [Gemini 3.8 Flash](gemini-3.8-flash-medium-2026-10-17.csv) | medium | 179 | 47.79 |

Each CSV is sorted by numeric `problem_id`. `score` is on the 0–100 scale;
all model means average the same 179 problems equally. Problem 61 is excluded
for every model because its output format changed. Sonnet runs for problems
16 and 93 ended without submissions; these rows now have score zero,
`trajectories=0`, and `provenance=missing_submission`.

For evaluated rows, `trajectories` counts the historical trajectories represented
by the problem-level aggregate (Sonnet problem 158 has two; all other evaluated
rows have one). `provenance` is `historical_submission` for previously selected
submissions or `trace_regeneration` for a submission reconstructed from recorded
templates and regenerated data. The reconstructed rows are GPT-6 Astra / 48 and
Sonnet 5.5 / 48, 143; they are not byte-identical recoveries of the original submissions.


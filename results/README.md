# Algorithmic per-problem scores (2026-10-17)

Scores for the [natural-log scoring rules](../README.md#scoring-principles),
exported from the 2026-10-17 rescoring results. These CSVs contain
existing evaluation results; exporting them did not run new model attempts.

| Model / CSV | Reasoning | Problems | Mean score |
|---|---|---:|---:|
| [Opus 5.5](opus-5.5-high-2026-10-17.csv) | high | 179 | 56.45 |
| [Sonnet 5.5](sonnet-5.5-max-2026-10-17.csv) | max | 177 | 54.45 |
| [GPT-6 Astra](gpt-6-astra-low-2026-10-17.csv) | low | 179 | 53.90 |
| [GPT-6 Sol](gpt-6-sol-high-2026-10-17.csv) | high | 179 | 52.35 |
| [Gemini 3.7 Flash](gemini-3.7-flash-medium-2026-10-17.csv) | medium | 179 | 47.92 |
| [Gemini 3.8 Flash](gemini-3.8-flash-medium-2026-10-17.csv) | medium | 179 | 47.69 |

Each CSV is sorted by numeric `problem_id` and preserves the source's score
precision. `score` is on the 0–100 scale; the displayed model mean averages the
available problems equally. `trajectories` is the number of evaluated
trajectories represented by that problem-level aggregate (Sonnet problem 158
has two; every other row has one).

`provenance` is `historical_submission` for previously selected submissions or
`trace_regeneration` for a submission reconstructed from recorded templates
and regenerated data. The reconstructed rows are GPT-6 Astra / 48 and
Sonnet 5.5 / 48, 143; they are not byte-identical recoveries of the original
submissions.

Problem 61 is excluded for all models because its output format changed.
Sonnet also lacks problems 16 and 93 because those runs ended without
submissions. Missing results are omitted, not filled with zero. Coverage is
179 problems per model, or 177 for Sonnet, out of the 180 retained problems;
the intersection shared by all models is 177 problems.

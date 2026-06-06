# Frontier-CS 2.0 Problems

This track contains open-ended optimization problems that do not fit cleanly
into the existing `algorithmic` or `research` tracks. Problems use the same
continuous scoring philosophy as Frontier-CS, but can define their own local
interfaces and evaluators.

To contribute a new 2.0 task, start with [CONTRIBUTING.md](CONTRIBUTING.md).
It documents the expected problem layout, evaluator contract, Harbor submission
modes, black-box safety rules, and validation commands.

## Erdos Unit Distance

The first 2.0 problem asks solvers to place a fixed number of planar points so
that as many pairs as possible have distance exactly `1`. Its problem ID is
`erdos_unit_distance`, matching the problem directory name. It is inspired by
the planar unit distance problem highlighted by OpenAI's May 2026 unit-distance
result.

## Erdos Unit Distance Demo

The demo variant uses the same interface and scoring rule with only `N = 10`
points. Its problem ID is `erdos_demo`. It is intended as a quick visual sanity
check for Harborized agent workflows before running the larger
`erdos_unit_distance` task.

## Vector DB ANN

This systems problem asks agents to build a Rust approximate nearest-neighbor
vector search service for a hidden SIFT1M-scale benchmark. Its problem ID is
`vector_db_ann`. Submissions are whole `/app` projects served through Harbor,
and the objective is to maximize effective QPS subject to `recall@10 >= 0.95`;
the score includes query throughput plus a small load/index-build penalty.

## Vector DB ANN Relaxed

This variant keeps the same SIFT1M-scale service contract and recall target as
`vector_db_ann`, but reduces the load/index-build penalty by 10x so stronger
offline indexing strategies are more viable. Its problem ID is
`vector_db_ann_relaxed`.

## BBOPlace ISPD2005

This VLSI placement problem asks agents to generate macro placement candidates
for the ISPD2005 benchmarks used by BBOPlace-Bench. Its problem ID is
`bboplace_ispd2005`. The public iterative feedback path evaluates the first
benchmark only, while the final verifier reruns the best iterative artifact and
the final submission across the full ISPD2005 suite. Scoring minimizes MP-HPWL
against relaxed MGO baselines and clips negative scores to zero. The task is
CPU-only and does not require DREAMPlace, GPU execution, or Ray.

## BBOPlace ICCAD2015

This VLSI placement problem uses the ICCAD2015 benchmark suite from
BBOPlace-Bench. Its problem ID is `bboplace_iccad2015`. It follows the same
candidate format, CPU-only evaluator, MP-HPWL metric, relaxed MGO baselines,
and quick-versus-final evaluation flow as `bboplace_ispd2005`, but scores the
ICCAD2015 benchmark set.

## BBOPlace Direct ISPD2005

This direct-placement variant asks agents to submit one JSON placement for a
single ISPD2005 design, `adaptec1`, instead of writing a Python placement
generator. Its problem ID is `bboplace_direct_ispd2005`. The evaluator uses the
same CPU-only BBOPlace MGO MP-HPWL path and relaxed baseline as the ISPD2005
suite task, but both iterative feedback and final verification score only that
one design.

## BBOPlace Direct ICCAD2015

This direct-placement variant asks agents to submit one JSON placement for a
single ICCAD2015 design, `superblue1`. Its problem ID is
`bboplace_direct_iccad2015`. It follows the same JSON interface and single
design evaluation flow as `bboplace_direct_ispd2005`, with the ICCAD2015
baseline for `superblue1`.

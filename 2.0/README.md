# Frontier-CS 2.0 Problems

This track contains open-ended optimization problems that do not fit cleanly
into the existing `algorithmic` or `research` tracks. Problems use the same
continuous scoring philosophy as Frontier-CS, but can define their own local
interfaces and evaluators.

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

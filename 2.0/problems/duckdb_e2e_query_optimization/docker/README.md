# Experimental DuckDB Images

This task needs DuckDB source trees in both the agent and judge containers.
The standard Frontier-CS 2.0 adapter can select Docker base images, but it does
not build problem-specific images by itself. Build these images before running
a local Harbor trial:

```bash
bash 2.0/problems/duckdb_e2e_query_optimization/docker/build_images.sh
```

Defaults:

```text
DUCKDB_REF=v1.5.3
DUCKDB_BUILD_JOBS=1
AGENT_TAG=frontiercs/duckdb-e2e-query-optimization-agent:experimental-v1.5.3
JUDGE_TAG=frontiercs/duckdb-e2e-query-optimization-judge:experimental-v1.5.3
```

The agent image contains:

```text
/app/duckdb
```

The judge image contains:

```text
/opt/duckdb-vanilla
/opt/duckdb-clean
```

`/opt/duckdb-clean` is prebuilt with:

```bash
CMAKE_BUILD_PARALLEL_LEVEL=1 GEN=ninja DISABLE_UNITY=1 DISABLE_PARQUET=1 BUILD_JEMALLOC=0 BUILD_BENCHMARK=1 BUILD_EXTENSIONS='tpch' make
```

`DUCKDB_BUILD_JOBS` intentionally defaults to `1`; higher parallelism can make
large DuckDB C++ objects exhaust Docker memory on local machines. Unity builds
are disabled for the same reason. Jemalloc is disabled because DuckDB v1.5.3's
non-unity build exposes a missing include in the jemalloc allocator wrapper;
vanilla and patched binaries are built with the same allocator setting.

The judge copies that prebuilt tree to `/opt/duckdb-vanilla` during image
construction. At evaluation time the evaluator first resets tracked files in
`/opt/duckdb-clean` back to `HEAD` and removes untracked files under `src`
without deleting ignored build artifacts, applies the submitted patch, performs
an incremental rebuild of the DuckDB shell and optional benchmark runner,
checks correctness against `/opt/duckdb-vanilla`, and then times TPC-H queries
through DuckDB's shell and TPC-H extension. Keeping build artifacts in the clean
tree is intentional; full DuckDB rebuilds are too slow for iterative Harbor
submissions.

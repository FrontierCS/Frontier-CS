#!/usr/bin/env bash
set -euo pipefail

AGENT_TAG="${AGENT_TAG:-frontiercs/duckdb-e2e-query-optimization-agent:experimental-v1.5.3}"
JUDGE_TAG="${JUDGE_TAG:-frontiercs/duckdb-e2e-query-optimization-judge:experimental-v1.5.3}"

echo "[agent] checking $AGENT_TAG"
docker run --rm "$AGENT_TAG" sh -lc '
  test -d /app/duckdb/.git
  git -C /app/duckdb rev-parse HEAD
'

echo "[judge] checking $JUDGE_TAG"
docker run --rm "$JUDGE_TAG" sh -lc '
  test -d /opt/duckdb-clean
  test -d /opt/duckdb-vanilla
  test -x /opt/duckdb-vanilla/build/release/duckdb
  test -x /opt/duckdb-vanilla/build/release/benchmark/benchmark_runner
  /opt/duckdb-vanilla/build/release/duckdb -c "LOAD tpch; SELECT count(*) FROM tpch_queries();"
'

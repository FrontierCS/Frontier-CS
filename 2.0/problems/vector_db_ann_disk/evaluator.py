#!/usr/bin/env python3
"""Evaluator for the Frontier-CS 2.0 Vector DB ANN Disk task."""

from __future__ import annotations

import json
import math
import os
import shutil
import socket
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib import request

import numpy as np


def _read_evaluation_config() -> dict[str, int]:
    config_path = Path(__file__).with_name("config.yaml")
    if not config_path.exists():
        return {}

    values: dict[str, int] = {}
    in_evaluation = False
    for raw_line in config_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line:
            continue
        if not raw_line.startswith((" ", "\t")):
            in_evaluation = line == "evaluation:"
            continue
        if not in_evaluation:
            continue
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"query_concurrency", "queries_per_worker"} and value:
            values[key] = int(value)
    return values


def _config_int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


_EVALUATION_CONFIG = _read_evaluation_config()
CONFIG_CONCURRENCY = int(_EVALUATION_CONFIG.get("query_concurrency", 8))
CONFIG_QUERIES_PER_WORKER = int(_EVALUATION_CONFIG.get("queries_per_worker", 64))


DIM = 128
N_BASE = _config_int("FRONTIER_VECTOR_DB_N", 100_000_000)
CONCURRENCY = _config_int("FRONTIER_VECTOR_DB_CONCURRENCY", CONFIG_CONCURRENCY)
QUERIES_PER_WORKER = _config_int(
    "FRONTIER_VECTOR_DB_QUERIES_PER_WORKER", CONFIG_QUERIES_PER_WORKER
)
N_QUERIES = _config_int(
    "FRONTIER_VECTOR_DB_Q", CONCURRENCY * QUERIES_PER_WORKER
)
TOP_K = _config_int("FRONTIER_VECTOR_DB_TOP_K", 10)
SEED = _config_int("FRONTIER_VECTOR_DB_SEED", 20260528)
GRAPH_DEGREE = _config_int("FRONTIER_VECTOR_DB_GRAPH_DEGREE", 64)
TARGET_RECALL = float(os.environ.get("FRONTIER_VECTOR_DB_TARGET_RECALL", "0.95"))
QUERY_NOISE = float(os.environ.get("FRONTIER_VECTOR_DB_QUERY_NOISE", "0.02"))
BUILD_TIMEOUT_SECONDS = _config_int("FRONTIER_VECTOR_DB_BUILD_TIMEOUT", 3600)
LOAD_TIMEOUT_SECONDS = _config_int("FRONTIER_VECTOR_DB_LOAD_TIMEOUT", 600)
WARMUP = _config_int("FRONTIER_VECTOR_DB_WARMUP", 32)
REFERENCE_BATCH_SIZE = _config_int("FRONTIER_VECTOR_DB_REFERENCE_BATCH_SIZE", 50_000)
LOCAL_GENERATION_LIMIT = _config_int(
    "FRONTIER_VECTOR_DB_LOCAL_GENERATION_LIMIT", 2_000_000
)
CACHE_DIR = Path(
    os.environ.get("FRONTIER_VECTOR_DB_CACHE", "/tmp/frontier_vector_db_ann_disk")
)

_BENCHMARK: "Benchmark | None" = None


@dataclass
class Benchmark:
    graph_path: Path
    vector_path: Path
    queries_path: Path
    truth: np.ndarray
    baseline_qps: float
    baseline_seconds: float
    baseline_load_seconds: float


def prepare() -> dict:
    print(
        f"[vector-db-ann-disk] preparing benchmark n_base={N_BASE} "
        f"n_queries={N_QUERIES} top_k={TOP_K} graph_degree={GRAPH_DEGREE}",
        flush=True,
    )
    benchmark = _ensure_benchmark()
    print(
        f"[vector-db-ann-disk] benchmark ready baseline_qps="
        f"{benchmark.baseline_qps:.6f} baseline_seconds="
        f"{benchmark.baseline_seconds:.6f} baseline_load_seconds="
        f"{benchmark.baseline_load_seconds:.6f}",
        flush=True,
    )
    return {
        "n_base": N_BASE,
        "n_queries": N_QUERIES,
        "top_k": TOP_K,
        "graph_degree": GRAPH_DEGREE,
        "baseline_qps": benchmark.baseline_qps,
        "baseline_seconds": benchmark.baseline_seconds,
        "baseline_load_seconds": benchmark.baseline_load_seconds,
    }


def _invalid(message: str, metrics: dict | None = None):
    return 0.0, 0.0, message, metrics or {}


def _copy_project(src: Path, dst: Path) -> None:
    ignore = shutil.ignore_patterns("target", ".git", ".frontier-cs")
    shutil.copytree(src, dst, ignore=ignore)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _post_json(url: str, payload: dict, timeout: float = 60.0) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _wait_for_server(
    port: int, deadline: float, process: subprocess.Popen | None = None
) -> None:
    last_error: Exception | None = None
    while time.time() < deadline:
        if process is not None and process.poll() is not None:
            stderr = b""
            if process.stderr is not None:
                stderr = process.stderr.read()[-800:]
            detail = stderr.decode("utf-8", errors="replace")
            suffix = f": {detail}" if detail else ""
            raise RuntimeError(f"server exited before becoming ready{suffix}")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1.0):
                pass
            return
        except Exception as exc:
            last_error = exc
            time.sleep(0.25)
    raise RuntimeError(f"server did not become ready: {last_error}")


def _write_vectors(path: Path, values: np.ndarray) -> None:
    values.astype(np.float32, copy=False).tofile(path)


def _load_vectors(path: Path, rows: int) -> np.memmap:
    return np.memmap(path, dtype=np.float32, mode="r", shape=(rows, DIM))


def _graph_vector_query_paths() -> tuple[Path, Path, Path, Path, Path]:
    default_dir = CACHE_DIR / (
        f"n{N_BASE}_d{DIM}_deg{GRAPH_DEGREE}_q{N_QUERIES}_k{TOP_K}_seed{SEED}"
    )
    benchmark_dir = Path(os.environ.get("FRONTIER_VECTOR_DB_BENCHMARK_DIR", default_dir))
    graph_path = Path(
        os.environ.get("FRONTIER_VECTOR_DB_GRAPH_PATH", benchmark_dir / "graph.bin")
    )
    vector_path = Path(
        os.environ.get("FRONTIER_VECTOR_DB_VECTOR_PATH", benchmark_dir / "vectors.bin")
    )
    queries_path = Path(
        os.environ.get("FRONTIER_VECTOR_DB_QUERY_PATH", benchmark_dir / "queries.bin")
    )
    truth_path = Path(
        os.environ.get("FRONTIER_VECTOR_DB_TRUTH_PATH", benchmark_dir / "truth.u32")
    )
    meta_path = Path(
        os.environ.get("FRONTIER_VECTOR_DB_BASELINE_PATH", benchmark_dir / "baseline.json")
    )
    return graph_path, vector_path, queries_path, truth_path, meta_path


def _check_file_size(path: Path, expected_bytes: int, label: str) -> bool:
    return path.exists() and path.stat().st_size == expected_bytes


def _generate_vectors(vector_path: Path, queries_path: Path) -> None:
    rng = np.random.default_rng(SEED)
    chunk = 50_000
    base = np.memmap(vector_path, dtype=np.float32, mode="w+", shape=(N_BASE, DIM))
    for start in range(0, N_BASE, chunk):
        end = min(start + chunk, N_BASE)
        base[start:end] = rng.standard_normal((end - start, DIM), dtype=np.float32)
    base.flush()

    ids = rng.integers(0, N_BASE, size=N_QUERIES)
    selected = np.asarray(base[ids], dtype=np.float32)
    noise = rng.standard_normal((N_QUERIES, DIM), dtype=np.float32) * QUERY_NOISE
    _write_vectors(queries_path, selected + noise)


def _generate_local_graph(graph_path: Path) -> None:
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    degree = min(GRAPH_DEGREE, max(0, N_BASE - 1))
    with graph_path.open("wb") as handle:
        handle.write(b"FCANNDK1")
        np.asarray([N_BASE], dtype=np.uint64).tofile(handle)
        np.asarray([DIM, degree], dtype=np.uint32).tofile(handle)
        if degree == 0:
            return
        chunk = 50_000
        offsets = np.arange(1, degree + 1, dtype=np.uint64)
        for start in range(0, N_BASE, chunk):
            end = min(start + chunk, N_BASE)
            ids = np.arange(start, end, dtype=np.uint64).reshape(-1, 1)
            neighbors = ((ids + offsets) % N_BASE).astype(np.uint32)
            degrees = np.full((end - start, 1), degree, dtype=np.uint32)
            np.concatenate([degrees, neighbors], axis=1).tofile(handle)


def _ensure_local_generation_allowed() -> None:
    if N_BASE <= LOCAL_GENERATION_LIMIT:
        return
    raise RuntimeError(
        "disk benchmark files were not found. Provide graph/vector/query/truth "
        "paths with FRONTIER_VECTOR_DB_* environment variables, or set "
        "FRONTIER_VECTOR_DB_N to a small value for local smoke testing."
    )


def _ensure_data_files(
    graph_path: Path, vector_path: Path, queries_path: Path, truth_path: Path, meta_path: Path
) -> None:
    expected_vector_bytes = N_BASE * DIM * 4
    expected_query_bytes = N_QUERIES * DIM * 4
    has_vectors = _check_file_size(vector_path, expected_vector_bytes, "vectors")
    has_queries = _check_file_size(queries_path, expected_query_bytes, "queries")

    if not has_vectors or not has_queries:
        _ensure_local_generation_allowed()
        print("[vector-db-ann-disk] generating local vectors", flush=True)
        vector_path.parent.mkdir(parents=True, exist_ok=True)
        queries_path.parent.mkdir(parents=True, exist_ok=True)
        _generate_vectors(vector_path, queries_path)
        truth_path.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)

    if not graph_path.exists():
        _ensure_local_generation_allowed()
        print("[vector-db-ann-disk] generating local graph", flush=True)
        _generate_local_graph(graph_path)


def _run_reference_server(port: int) -> None:
    import faiss

    index: faiss.IndexIDMap | None = None

    class ReferenceHandler(BaseHTTPRequestHandler):
        server_version = "FrontierVectorDiskReference/1.0"

        def _write_json(self, status: int, payload: dict) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._write_json(200, {"status": "ok"})
                return
            self._write_json(404, {"status": "error", "error": "not found"})

        def do_POST(self) -> None:
            nonlocal index
            if self.path == "/load":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    graph_path = Path(payload["graph_path"])
                    vector_path = Path(payload["vector_path"])
                    if not graph_path.exists():
                        raise FileNotFoundError(f"graph_path not found: {graph_path}")
                    if not vector_path.exists():
                        raise FileNotFoundError(f"vector_path not found: {vector_path}")

                    base = _load_vectors(vector_path, N_BASE)
                    new_index = faiss.IndexIDMap(faiss.IndexFlatL2(DIM))
                    for start in range(0, N_BASE, REFERENCE_BATCH_SIZE):
                        end = min(start + REFERENCE_BATCH_SIZE, N_BASE)
                        vectors = np.asarray(base[start:end], dtype=np.float32)
                        ids = np.arange(start, end, dtype=np.int64)
                        new_index.add_with_ids(vectors, ids)
                    index = new_index
                    self._write_json(200, {"status": "ok"})
                except Exception as exc:
                    self._write_json(400, {"status": "error", "error": str(exc)})
                return

            if self.path != "/search":
                self._write_json(404, {"status": "error", "error": "not found"})
                return

            try:
                if index is None:
                    raise RuntimeError("reference index has not been loaded")
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                vector = np.asarray(payload["vector"], dtype=np.float32)
                top_k = int(payload.get("top_k", TOP_K))
                if vector.shape != (DIM,):
                    raise ValueError("query vector has wrong dimension")
                if top_k != TOP_K:
                    raise ValueError("unexpected top_k")
                distances, ids = index.search(vector.reshape(1, DIM), top_k)
                results = [
                    {"id": int(id_), "distance": float(distance)}
                    for id_, distance in zip(ids[0], distances[0])
                ]
                self._write_json(200, {"results": results})
            except Exception as exc:
                self._write_json(400, {"status": "error", "error": str(exc)})

        def log_message(self, fmt: str, *args: object) -> None:
            return

    ThreadingHTTPServer(("127.0.0.1", port), ReferenceHandler).serve_forever()


def _load_service(base_url: str, graph_path: Path, vector_path: Path) -> float:
    start = time.perf_counter()
    response = _post_json(
        f"{base_url}/load",
        {"graph_path": str(graph_path), "vector_path": str(vector_path)},
        timeout=LOAD_TIMEOUT_SECONDS,
    )
    load_seconds = max(time.perf_counter() - start, 1e-9)
    if response.get("status") != "ok":
        raise ValueError(f"load response did not report ok: {response}")
    if load_seconds > LOAD_TIMEOUT_SECONDS:
        raise TimeoutError(f"load timed out after {LOAD_TIMEOUT_SECONDS}s")
    return load_seconds


def _measure_reference_baseline(
    graph_path: Path, vector_path: Path, queries: np.ndarray
) -> tuple[np.ndarray, list[float], float, float]:
    port = _free_port()
    process = subprocess.Popen(
        ["python3", str(Path(__file__).resolve()), "--reference-server", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        _wait_for_server(port, time.time() + 120, process)
        load_seconds = _load_service(f"http://127.0.0.1:{port}", graph_path, vector_path)
        results, latencies, baseline_seconds = _run_queries(
            f"http://127.0.0.1:{port}", queries
        )
        return results, latencies, baseline_seconds, load_seconds
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def _ensure_benchmark() -> Benchmark:
    global _BENCHMARK
    if _BENCHMARK is not None:
        return _BENCHMARK

    graph_path, vector_path, queries_path, truth_path, meta_path = (
        _graph_vector_query_paths()
    )
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    vector_path.parent.mkdir(parents=True, exist_ok=True)
    queries_path.parent.mkdir(parents=True, exist_ok=True)
    truth_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.parent.mkdir(parents=True, exist_ok=True)

    _ensure_data_files(graph_path, vector_path, queries_path, truth_path, meta_path)

    expected_vector_bytes = N_BASE * DIM * 4
    expected_query_bytes = N_QUERIES * DIM * 4
    if not _check_file_size(vector_path, expected_vector_bytes, "vectors"):
        raise RuntimeError(f"vectors file has unexpected size: {vector_path}")
    if not _check_file_size(queries_path, expected_query_bytes, "queries"):
        raise RuntimeError(f"queries file has unexpected size: {queries_path}")

    queries = _load_vectors(queries_path, N_QUERIES)

    if truth_path.exists() and meta_path.exists():
        truth = np.fromfile(truth_path, dtype=np.uint32).reshape(N_QUERIES, TOP_K)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        baseline_seconds = float(meta["baseline_seconds"])
        baseline_qps = float(meta["baseline_qps"])
        baseline_load_seconds = float(meta["baseline_load_seconds"])
    else:
        if N_BASE > LOCAL_GENERATION_LIMIT:
            raise RuntimeError(
                "truth/baseline files were not found and the local exact reference "
                "is disabled for this benchmark size"
            )
        print("[vector-db-ann-disk] running Faiss HTTP exact baseline", flush=True)
        truth, _, baseline_seconds, baseline_load_seconds = _measure_reference_baseline(
            graph_path, vector_path, queries
        )
        truth.astype(np.uint32, copy=False).tofile(truth_path)
        baseline_qps = N_QUERIES / baseline_seconds
        meta_path.write_text(
            json.dumps(
                {
                    "baseline_seconds": baseline_seconds,
                    "baseline_qps": baseline_qps,
                    "baseline_load_seconds": baseline_load_seconds,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    _BENCHMARK = Benchmark(
        graph_path=graph_path,
        vector_path=vector_path,
        queries_path=queries_path,
        truth=truth,
        baseline_qps=baseline_qps,
        baseline_seconds=baseline_seconds,
        baseline_load_seconds=baseline_load_seconds,
    )
    return _BENCHMARK


def _search_one(base_url: str, query_index: int, vector: np.ndarray) -> tuple[int, list[int], float]:
    start = time.perf_counter()
    response = _post_json(
        f"{base_url}/search",
        {"vector": vector.astype(float).tolist(), "top_k": TOP_K},
        timeout=120.0,
    )
    latency_ms = (time.perf_counter() - start) * 1000.0
    ids = [int(item.get("id", -1)) for item in response.get("results", [])[:TOP_K]]
    return query_index, ids, latency_ms


def _run_queries(
    base_url: str, queries: np.ndarray
) -> tuple[np.ndarray, list[float], float]:
    for i in range(min(WARMUP, N_QUERIES)):
        try:
            _search_one(base_url, i, queries[i])
        except Exception:
            pass

    results = np.zeros((N_QUERIES, TOP_K), dtype=np.uint32)
    latencies: list[float] = []
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        futures = [
            pool.submit(_search_one, base_url, i, queries[i])
            for i in range(N_QUERIES)
        ]
        for future in as_completed(futures):
            query_index, ids, latency_ms = future.result()
            if len(ids) != TOP_K:
                raise ValueError("search response did not contain top_k results")
            if len(set(ids)) != len(ids):
                raise ValueError("search response contains duplicate vector ids")
            if any(id_ < 0 or id_ >= N_BASE for id_ in ids):
                raise ValueError("search response contains an out-of-range vector id")
            results[query_index] = np.asarray(ids, dtype=np.uint32)
            latencies.append(latency_ms)
    duration = max(time.perf_counter() - start, 1e-9)
    return results, latencies, duration


def _recall_at_k(results: np.ndarray, truth: np.ndarray) -> float:
    hits = 0
    for got, expected in zip(results, truth):
        hits += len(set(int(x) for x in got) & set(int(x) for x in expected))
    return hits / float(N_QUERIES * TOP_K)


def evaluate(solution_path: str):
    root = Path(solution_path)
    if not root.is_dir():
        return _invalid("submission path must be a Rust project directory")
    if not (root / "Cargo.toml").exists():
        return _invalid("Cargo.toml not found in submission directory")

    try:
        benchmark = _ensure_benchmark()
    except Exception as exc:
        return _invalid(f"benchmark preparation failed: {exc}")

    with tempfile.TemporaryDirectory(prefix="frontier_vector_db_ann_disk_") as tmp:
        workdir = Path(tmp) / "project"
        _copy_project(root, workdir)
        try:
            subprocess.run(
                ["cargo", "build", "--release", "--quiet"],
                cwd=workdir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=BUILD_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            return _invalid("cargo build timed out")
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.decode("utf-8", errors="replace")
            return _invalid(f"cargo build failed: {stderr[-800:]}")

        queries = _load_vectors(benchmark.queries_path, N_QUERIES)
        port = _free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen(
            ["cargo", "run", "--release", "--quiet"],
            cwd=workdir,
            env={**os.environ, "PORT": str(port)},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        load_seconds = 0.0
        try:
            _wait_for_server(port, time.time() + 30, process)
            load_seconds = _load_service(
                base_url, benchmark.graph_path, benchmark.vector_path
            )
            results, latencies, candidate_seconds = _run_queries(base_url, queries)
        except Exception as exc:
            stderr = b""
            if process.poll() is not None and process.stderr is not None:
                stderr = process.stderr.read()[-800:]
            metrics = {
                "baseline_qps": benchmark.baseline_qps,
                "baseline_seconds": benchmark.baseline_seconds,
                "baseline_load_seconds": benchmark.baseline_load_seconds,
                "qps": 0.0,
                "candidate_seconds": 0.0,
                "load_seconds": load_seconds,
                "recall_at_10": 0.0,
            }
            detail = stderr.decode("utf-8", errors="replace")
            suffix = f": {detail}" if detail else ""
            return _invalid(f"candidate benchmark failed: {exc}{suffix}", metrics)
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

    recall = _recall_at_k(results, benchmark.truth)
    qps = N_QUERIES / candidate_seconds
    if recall < TARGET_RECALL or qps <= benchmark.baseline_qps:
        score = 0.0
    else:
        score = 100.0 * (1.0 - math.sqrt(benchmark.baseline_qps) / math.sqrt(qps))

    metrics = {
        "qps": qps,
        "baseline_qps": benchmark.baseline_qps,
        "recall_at_10": recall,
        "candidate_seconds": candidate_seconds,
        "load_seconds": load_seconds,
        "baseline_seconds": benchmark.baseline_seconds,
        "baseline_load_seconds": benchmark.baseline_load_seconds,
        "avg_latency_ms": float(np.mean(latencies)) if latencies else 0.0,
        "p50_latency_ms": float(np.percentile(latencies, 50)) if latencies else 0.0,
        "p95_latency_ms": float(np.percentile(latencies, 95)) if latencies else 0.0,
        "p99_latency_ms": float(np.percentile(latencies, 99)) if latencies else 0.0,
        "concurrency": float(CONCURRENCY),
        "n_base": float(N_BASE),
        "n_queries": float(N_QUERIES),
        "top_k": float(TOP_K),
        "graph_degree": float(GRAPH_DEGREE),
    }
    message = (
        f"N={N_BASE}; Q={N_QUERIES}; top_k={TOP_K}; "
        f"recall_at_10={recall:.6f}; qps={qps:.6f}; "
        f"baseline_qps={benchmark.baseline_qps:.6f}; "
        f"load_seconds={load_seconds:.6f}; score={score:.6f}"
    )
    return score, score, message, metrics


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--reference-server":
        _run_reference_server(int(sys.argv[2]))
        raise SystemExit(0)

    if len(sys.argv) != 2:
        print("usage: evaluator.py /path/to/rust/project", file=sys.stderr)
        raise SystemExit(2)
    bounded, unbounded, detail, metrics = evaluate(sys.argv[1])
    print(detail)
    print(json.dumps(metrics, indent=2))
    print(f"{bounded:.12f} {unbounded:.12f}")

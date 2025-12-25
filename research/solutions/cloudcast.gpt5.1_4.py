import json
import os
import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        config_map = {}
        num_vms = 2
        default_ingress = {"aws": 10, "gcp": 16, "azure": 16}
        default_egress = {"aws": 5, "gcp": 7, "azure": 16}

        if spec_path is not None:
            try:
                with open(spec_path, "r") as f:
                    spec = json.load(f)
                if isinstance(spec, dict):
                    try:
                        num_vms = int(spec.get("num_vms", num_vms))
                    except Exception:
                        num_vms = 2
                    config_files = spec.get("config_files", [])
                    base_dir = os.path.dirname(os.path.abspath(spec_path))
                    for cfg_rel_path in config_files:
                        cfg_path = cfg_rel_path
                        if not os.path.isabs(cfg_path):
                            cfg_path = os.path.join(base_dir, cfg_rel_path)
                        try:
                            with open(cfg_path, "r") as cf:
                                cfg = json.load(cf)
                        except Exception:
                            continue
                        try:
                            src = cfg["source_node"]
                            dsts = cfg["dest_nodes"]
                            np = int(cfg["num_partitions"])
                        except Exception:
                            continue
                        key = (src, tuple(sorted(dsts)), np)
                        config_map[key] = {
                            "data_vol": cfg.get("data_vol", 300.0),
                            "num_partitions": np,
                            "ingress_limit": cfg.get("ingress_limit", default_ingress),
                            "egress_limit": cfg.get("egress_limit", default_egress),
                        }
            except Exception:
                pass

        lines = []
        lines.append("import networkx as nx")
        lines.append("from itertools import islice")
        lines.append(f"GLOBAL_CONFIGS = {repr(config_map)}")
        lines.append(f"GLOBAL_NUM_VMS = {int(num_vms)}")
        lines.append(f"DEFAULT_INGRESS_LIMIT = {repr(default_ingress)}")
        lines.append(f"DEFAULT_EGRESS_LIMIT = {repr(default_egress)}")
        lines.append("R_INSTANCE = 0.54  # $/hour")

        lines.append(
            textwrap.dedent(
                """
                class BroadCastTopology:
                    def __init__(self, src: str, dsts: list, num_partitions: int):
                        self.src = src
                        self.dsts = dsts
                        self.num_partitions = int(num_partitions)
                        # Structure: {dst: {partition_id: [edges]}}
                        # Each edge is [src_node, dst_node, edge_data_dict]
                        self.paths = {dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts}

                    def append_dst_partition_path(self, dst: str, partition: int, path: list):
                        partition = str(partition)
                        if self.paths[dst][partition] is None:
                            self.paths[dst][partition] = []
                        self.paths[dst][partition].append(path)

                    def set_dst_partition_paths(self, dst: str, partition: int, paths: list):
                        partition = str(partition)
                        self.paths[dst][partition] = paths

                    def set_num_partitions(self, num_partitions: int):
                        self.num_partitions = num_partitions
                """
            ).strip("\n")
        )

        lines.append(
            textwrap.dedent(
                """
                def _get_provider(node):
                    if not isinstance(node, str):
                        return None
                    parts = node.split(":", 1)
                    if len(parts) != 2:
                        return None
                    prov = parts[0].lower()
                    if prov in DEFAULT_INGRESS_LIMIT or prov in DEFAULT_EGRESS_LIMIT:
                        return prov
                    return None


                def _approx_edge_capacity(u, v, data, ingress_limit, egress_limit, num_vms):
                    thr = data.get("throughput", None)
                    if thr is None:
                        thr = 1.0
                    try:
                        cap = float(thr)
                    except Exception:
                        cap = 1.0

                    prov_u = _get_provider(u)
                    prov_v = _get_provider(v)

                    if prov_u in egress_limit:
                        try:
                            cap = min(cap, float(egress_limit[prov_u]) * float(num_vms))
                        except Exception:
                            pass
                    if prov_v in ingress_limit:
                        try:
                            cap = min(cap, float(ingress_limit[prov_v]) * float(num_vms))
                        except Exception:
                            pass

                    if cap <= 0:
                        cap = 1e-6
                    return cap


                def _build_edge_caps(G, ingress_limit, egress_limit, num_vms):
                    edge_caps = {}
                    for u, v, data in G.edges(data=True):
                        edge_caps[(u, v)] = _approx_edge_capacity(u, v, data, ingress_limit, egress_limit, num_vms)
                    return edge_caps


                def _get_candidate_paths(G, src, dst, edge_caps, max_paths=3):
                    paths = []
                    seen = set()

                    def cost_weight(u, v, data):
                        c = data.get("cost", 0.0)
                        if c is None:
                            c = 0.0
                        try:
                            return float(c) + 1e-9
                        except Exception:
                            return 1e-9

                    def inv_cap_weight(u, v, data):
                        cap = edge_caps.get((u, v), data.get("throughput", 1.0) or 1.0)
                        try:
                            cap = float(cap)
                        except Exception:
                            cap = 1.0
                        if cap <= 0:
                            cap = 1e-6
                        return 1.0 / cap

                    def composite_weight(u, v, data):
                        c = data.get("cost", 0.0)
                        if c is None:
                            c = 0.0
                        cap = edge_caps.get((u, v), data.get("throughput", 1.0) or 1.0)
                        try:
                            cap = float(cap)
                        except Exception:
                            cap = 1.0
                        if cap <= 0:
                            cap = 1e-6
                        # Slight preference for higher throughput while keeping cost dominant
                        return float(c) + 0.05 / cap

                    # Cost-based shortest paths
                    try:
                        for p in islice(nx.shortest_simple_paths(G, src, dst, weight=cost_weight), max_paths):
                            t = tuple(p)
                            if t not in seen:
                                seen.add(t)
                                paths.append(p)
                    except Exception:
                        pass

                    remaining = max_paths - len(paths)
                    if remaining > 0:
                        # Throughput-based shortest paths
                        try:
                            for p in islice(nx.shortest_simple_paths(G, src, dst, weight=inv_cap_weight), remaining):
                                t = tuple(p)
                                if t not in seen:
                                    seen.add(t)
                                    paths.append(p)
                        except Exception:
                            pass

                    remaining = max_paths - len(paths)
                    if remaining > 0:
                        # Composite metric paths
                        try:
                            for p in islice(nx.shortest_simple_paths(G, src, dst, weight=composite_weight), remaining):
                                t = tuple(p)
                                if t not in seen:
                                    seen.add(t)
                                    paths.append(p)
                        except Exception:
                            pass

                    if not paths:
                        # Robust fallback: plain Dijkstra on cost, else unweighted shortest path
                        try:
                            def _w(u, v, data):
                                c = data.get("cost", 0.0)
                                if c is None:
                                    c = 0.0
                                return float(c)
                            p = nx.dijkstra_path(G, src, dst, weight=_w)
                        except Exception:
                            p = nx.shortest_path(G, src, dst)
                        paths = [p]

                    return paths


                def _precompute_path_metrics(G, paths, edge_caps):
                    metrics = []
                    for p in paths:
                        edges = []
                        total_cost = 0.0
                        bottleneck = None
                        for i in range(len(p) - 1):
                            u = p[i]
                            v = p[i + 1]
                            data = G[u][v]
                            edges.append((u, v, data))
                            c = data.get("cost", 0.0)
                            if c is None:
                                c = 0.0
                            try:
                                total_cost += float(c)
                            except Exception:
                                pass
                            cap = edge_caps.get((u, v), data.get("throughput", 1.0) or 1.0)
                            try:
                                cap = float(cap)
                            except Exception:
                                cap = 1.0
                            if cap <= 0:
                                cap = 1e-6
                            if bottleneck is None or cap < bottleneck:
                                bottleneck = cap
                        if bottleneck is None:
                            bottleneck = 1.0
                        metrics.append(
                            {
                                "nodes": p,
                                "edges": edges,
                                "cost": total_cost,
                                "cap": bottleneck,
                            }
                        )
                    return metrics


                def _enumerate_allocations(N, K):
                    if K == 1:
                        yield (N,)
                        return

                    alloc = [0] * K

                    def rec(pos, remaining):
                        if pos == K - 1:
                            alloc[pos] = remaining
                            yield tuple(alloc)
                            return
                        for x in range(remaining + 1):
                            alloc[pos] = x
                            for t in rec(pos + 1, remaining - x):
                                yield t

                    for t in rec(0, N):
                        yield t
                """
            ).strip("\n")
        )

        lines.append(
            textwrap.dedent(
                """
                def search_algorithm(src: str, dsts: list, G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
                    # Normalize inputs
                    if num_partitions is None:
                        num_partitions = 1
                    num_partitions = int(num_partitions)
                    dsts_list = list(dsts)

                    key = (src, tuple(sorted(dsts_list)), num_partitions)
                    cfg = GLOBAL_CONFIGS.get(key, None)

                    if cfg is not None:
                        try:
                            data_vol = float(cfg.get("data_vol", 300.0))
                        except Exception:
                            data_vol = 300.0
                        ingress_limit = cfg.get("ingress_limit", DEFAULT_INGRESS_LIMIT)
                        egress_limit = cfg.get("egress_limit", DEFAULT_EGRESS_LIMIT)
                    else:
                        # Fallback to defaults if config not found
                        data_vol = 300.0
                        ingress_limit = DEFAULT_INGRESS_LIMIT
                        egress_limit = DEFAULT_EGRESS_LIMIT

                    num_vms = GLOBAL_NUM_VMS if GLOBAL_NUM_VMS is not None else 2
                    if num_vms <= 0:
                        num_vms = 2

                    if num_partitions <= 0:
                        num_partitions = 1

                    s_partition = data_vol / float(num_partitions)

                    # Approximate instance cost weight based on graph size
                    approx_V = max(len(getattr(G, "nodes", []) or []), 1)
                    w_time = approx_V * float(num_vms) * (R_INSTANCE / 3600.0)

                    edge_caps = _build_edge_caps(G, ingress_limit, egress_limit, num_vms)

                    bc_topology = BroadCastTopology(src, dsts_list, num_partitions)

                    for dst in dsts_list:
                        try:
                            candidate_paths = _get_candidate_paths(G, src, dst, edge_caps, max_paths=3)
                        except Exception:
                            # Fallback to basic Dijkstra if candidate path generation fails
                            try:
                                def _w(u, v, data):
                                    c = data.get("cost", 0.0)
                                    if c is None:
                                        c = 0.0
                                    return float(c)
                                p = nx.dijkstra_path(G, src, dst, weight=_w)
                            except Exception:
                                p = nx.shortest_path(G, src, dst)
                            candidate_paths = [p]

                        path_metrics = _precompute_path_metrics(G, candidate_paths, edge_caps)
                        K = len(path_metrics)
                        N = num_partitions

                        if K == 0 or N <= 0:
                            continue

                        if K == 1 or N == 1:
                            alloc = (N,)
                        else:
                            # Use exhaustive allocation search when problem size is small
                            if N <= 25 and K <= 4:
                                best_obj = None
                                best_alloc = None
                                for alloc_try in _enumerate_allocations(N, K):
                                    approx_egress = 0.0
                                    max_time = 0.0
                                    for j, k in enumerate(alloc_try):
                                        if k <= 0:
                                            continue
                                        pm = path_metrics[j]
                                        approx_egress += k * s_partition * pm["cost"]
                                        t_j = (k * s_partition * 8.0) / pm["cap"]
                                        if t_j > max_time:
                                            max_time = t_j
                                    total_obj = approx_egress + w_time * max_time
                                    if best_obj is None or total_obj < best_obj:
                                        best_obj = total_obj
                                        best_alloc = alloc_try
                                alloc = best_alloc
                            else:
                                # Heuristic allocation for larger N
                                weights = []
                                for pm in path_metrics:
                                    cost = pm["cost"]
                                    cap = pm["cap"]
                                    if cost is None or cost <= 0:
                                        denom = 1e-6
                                    else:
                                        denom = float(cost)
                                    try:
                                        cap_val = float(cap)
                                    except Exception:
                                        cap_val = 1.0
                                    if cap_val <= 0:
                                        cap_val = 1e-6
                                    weights.append(cap_val / denom)

                                sum_w = sum(weights)
                                if sum_w <= 0:
                                    alloc_list = [0] * K
                                    alloc_list[0] = N
                                else:
                                    alloc_list = [int(N * w / sum_w) for w in weights]
                                    rem = N - sum(alloc_list)
                                    # Distribute remaining partitions to best (cheap & fast) paths
                                    scores = []
                                    for idx, pm in enumerate(path_metrics):
                                        cap_val = pm["cap"]
                                        if cap_val <= 0:
                                            cap_val = 1e-6
                                        scores.append((pm["cost"] / cap_val, idx))
                                    scores.sort()
                                    i = 0
                                    while rem > 0 and scores:
                                        idx = scores[i % len(scores)][1]
                                        alloc_list[idx] += 1
                                        rem -= 1
                                        i += 1
                                alloc = tuple(alloc_list)

                        # Map partitions to paths according to allocation
                        assignment = [0] * N
                        pos = 0
                        for j, k in enumerate(alloc):
                            for _ in range(k):
                                if pos < N:
                                    assignment[pos] = j
                                    pos += 1
                        while pos < N:
                            assignment[pos] = 0
                            pos += 1

                        # Write paths into BroadCastTopology
                        for part_id in range(N):
                            path_idx = assignment[part_id]
                            pm = path_metrics[path_idx]
                            edge_list = []
                            for (u, v, data) in pm["edges"]:
                                edge_list.append([u, v, data])
                            bc_topology.set_dst_partition_paths(dst, part_id, edge_list)

                    return bc_topology
                """
            ).strip("\n")
        )

        code = "\n\n".join(lines)
        return {"code": code}

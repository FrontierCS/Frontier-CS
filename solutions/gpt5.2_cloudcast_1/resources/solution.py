import json
import os
import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        if spec_path and os.path.exists(spec_path):
            try:
                with open(spec_path, "r", encoding="utf-8") as f:
                    spec = json.load(f)
                if isinstance(spec, dict) and "num_vms" in spec:
                    num_vms = int(spec["num_vms"])
            except Exception:
                num_vms = 2

        algo_code = textwrap.dedent(
            f"""
            import math
            import networkx as nx

            N_VMS = {int(num_vms)}
            INSTANCE_RATE_PER_HOUR = 0.54

            DEFAULT_INGRESS_LIMIT = {{"aws": 10.0, "gcp": 16.0, "azure": 16.0}}
            DEFAULT_EGRESS_LIMIT  = {{"aws": 5.0,  "gcp": 7.0,  "azure": 16.0}}

            class BroadCastTopology:
                def __init__(self, src: str, dsts: list[str], num_partitions: int):
                    self.src = src
                    self.dsts = dsts
                    self.num_partitions = int(num_partitions)
                    self.paths = {{dst: {{str(i): None for i in range(self.num_partitions)}} for dst in dsts}}

                def append_dst_partition_path(self, dst: str, partition: int, path: list):
                    partition = str(partition)
                    if self.paths[dst][partition] is None:
                        self.paths[dst][partition] = []
                    self.paths[dst][partition].append(path)

                def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
                    partition = str(partition)
                    self.paths[dst][partition] = paths

                def set_num_partitions(self, num_partitions: int):
                    self.num_partitions = num_partitions


            def _provider(node: str) -> str:
                if not node:
                    return ""
                i = node.find(":")
                if i <= 0:
                    return node.lower()
                return node[:i].lower()


            def _safe_thr(val) -> float:
                try:
                    x = float(val)
                except Exception:
                    return 1e-9
                if x <= 0.0:
                    return 1e-9
                return x


            def _safe_cost(val) -> float:
                try:
                    return float(val)
                except Exception:
                    return 0.0


            def _path_nodes_to_edges(G: nx.DiGraph, nodes: list[str]) -> list:
                edges = []
                for i in range(len(nodes) - 1):
                    u = nodes[i]
                    v = nodes[i + 1]
                    if u == v:
                        return []
                    if not G.has_edge(u, v):
                        return []
                    edges.append([u, v, G[u][v]])
                return edges


            def _path_cost(G: nx.DiGraph, nodes: list[str]) -> float:
                s = 0.0
                for i in range(len(nodes) - 1):
                    u = nodes[i]
                    v = nodes[i + 1]
                    if G.has_edge(u, v):
                        s += _safe_cost(G[u][v].get("cost", 0.0))
                    else:
                        return float("inf")
                return s


            def _try_shortest_simple_paths(G: nx.DiGraph, src: str, dst: str, k: int, max_len: int):
                out = []
                try:
                    gen = nx.shortest_simple_paths(G, src, dst, weight="cost")
                    for path in gen:
                        if len(path) <= max_len:
                            out.append(path)
                        if len(out) >= k:
                            break
                except Exception:
                    return out
                return out


            def _dijkstra_path_custom(G: nx.DiGraph, src: str, dst: str, weight_fn):
                try:
                    return nx.dijkstra_path(G, src, dst, weight=weight_fn)
                except Exception:
                    return None


            def _generate_candidate_paths(G: nx.DiGraph, src: str, dst: str):
                MAX_LEN = 10
                paths = []

                # k-shortest by egress cost
                for p in _try_shortest_simple_paths(G, src, dst, k=3, max_len=MAX_LEN):
                    paths.append(p)

                # high-throughput preference path
                def w_thr(u, v, d):
                    thr = _safe_thr(d.get("throughput", 1e-9))
                    return 1.0 / thr

                p_thr = _dijkstra_path_custom(G, src, dst, w_thr)
                if p_thr and len(p_thr) <= MAX_LEN:
                    paths.append(p_thr)

                # cost + small throughput penalty
                def w_mix(u, v, d):
                    c = _safe_cost(d.get("cost", 0.0))
                    thr = _safe_thr(d.get("throughput", 1e-9))
                    return c + 0.02 * (1.0 / thr)

                p_mix = _dijkstra_path_custom(G, src, dst, w_mix)
                if p_mix and len(p_mix) <= MAX_LEN:
                    paths.append(p_mix)

                # de-duplicate while preserving order
                seen = set()
                uniq = []
                for p in paths:
                    t = tuple(p)
                    if t not in seen:
                        seen.add(t)
                        uniq.append(p)
                if not uniq:
                    try:
                        p0 = nx.shortest_path(G, src, dst)
                        uniq = [p0]
                    except Exception:
                        uniq = []
                return uniq


            def _compute_total_cost(dsts, num_partitions, assign, cand_edges, cand_edge_sets):
                edge_counts = {{}}
                out_used = {{}}
                in_used = {{}}
                nodes_used = set()
                egress_cost = 0.0

                # edge -> list of (dst, p) using it
                edge_to_pairs = {{}}

                for dst in dsts:
                    ap = assign[dst]
                    ce = cand_edges[dst]
                    for p in range(num_partitions):
                        idx = ap[p]
                        edges = ce[idx]
                        for e in edges:
                            u, v, data = e
                            key = (u, v)
                            edge_counts[key] = edge_counts.get(key, 0) + 1
                            egress_cost += _safe_cost(data.get("cost", 0.0))
                            if u not in out_used:
                                out_used[u] = set()
                            out_used[u].add(v)
                            if v not in in_used:
                                in_used[v] = set()
                            in_used[v].add(u)
                            nodes_used.add(u)
                            nodes_used.add(v)
                            lst = edge_to_pairs.get(key)
                            if lst is None:
                                edge_to_pairs[key] = [(dst, p)]
                            else:
                                if len(lst) < 200:
                                    lst.append((dst, p))

                if not edge_counts:
                    return 0.0, None, [], {{}}

                out_deg = {{u: len(s) for u, s in out_used.items()}}
                in_deg = {{v: len(s) for v, s in in_used.items()}}

                out_share = {{}}
                for u, deg in out_deg.items():
                    prov = _provider(u)
                    lim = DEFAULT_EGRESS_LIMIT.get(prov, 10.0) * float(N_VMS)
                    out_share[u] = lim / float(deg) if deg > 0 else lim

                in_share = {{}}
                for v, deg in in_deg.items():
                    prov = _provider(v)
                    lim = DEFAULT_INGRESS_LIMIT.get(prov, 10.0) * float(N_VMS)
                    in_share[v] = lim / float(deg) if deg > 0 else lim

                max_time = 0.0
                worst_edge = None
                edge_time = {{}}

                for (u, v), cnt in edge_counts.items():
                    # Need edge throughput; obtain from any candidate edge dict is fine, but simplest: use current graph edge data access is not available here.
                    # We will approximate by using minimum throughput among candidate edges that match (u,v) via stored sets:
                    # However, we have no per-(u,v) data dict stored here; use a conservative default if missing.
                    thr = None
                    # Find a data dict from one of the candidate paths that contains (u,v)
                    # To keep this fast, we avoid scanning all; instead, compute thr from a representative by looking at any pair list and reusing its chosen path.
                    # We'll just set thr high and rely on node shares; but we can do better by storing per-edge throughput separately externally.
                    # This function will be called with globally accessible EDGE_THR map via closure assignment in search_algorithm.
                    thr = EDGE_THR.get((u, v), 1e-9)

                    f = thr
                    so = out_share.get(u)
                    if so is not None and so < f:
                        f = so
                    si = in_share.get(v)
                    if si is not None and si < f:
                        f = si
                    if f <= 1e-12:
                        f = 1e-12
                    t = (float(cnt) * 8.0) / f
                    edge_time[(u, v)] = t
                    if t > max_time:
                        max_time = t
                        worst_edge = (u, v)

                instance_cost = float(len(nodes_used)) * float(N_VMS) * (float(INSTANCE_RATE_PER_HOUR) / 3600.0) * max_time
                total = egress_cost + instance_cost

                pairs = edge_to_pairs.get(worst_edge, []) if worst_edge is not None else []
                return total, worst_edge, pairs, edge_time


            def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
                num_partitions = int(num_partitions)
                bc = BroadCastTopology(src, dsts, num_partitions)

                # Precompute edge throughput for fast evaluation
                global EDGE_THR
                EDGE_THR = {{}}
                for u, v, d in G.edges(data=True):
                    EDGE_THR[(u, v)] = _safe_thr(d.get("throughput", 1e-9))

                # Candidate paths per destination
                cand_edges = {{}}
                cand_edge_sets = {{}}
                for dst in dsts:
                    node_paths = _generate_candidate_paths(G, src, dst)
                    edges_list = []
                    edge_sets = []
                    costs = []
                    for np in node_paths:
                        el = _path_nodes_to_edges(G, np)
                        if not el:
                            continue
                        es = set((e[0], e[1]) for e in el)
                        edges_list.append(el)
                        edge_sets.append(es)
                        costs.append(_path_cost(G, np))
                    if not edges_list:
                        # last resort: unweighted shortest path
                        try:
                            np = nx.shortest_path(G, src, dst)
                            el = _path_nodes_to_edges(G, np)
                            if not el:
                                raise RuntimeError("no valid path")
                            edges_list = [el]
                            edge_sets = [set((e[0], e[1]) for e in el)]
                            costs = [_path_cost(G, np)]
                        except Exception:
                            # If still no path, create empty placeholders (will fail evaluator anyway)
                            edges_list = [[]]
                            edge_sets = [set()]
                            costs = [float("inf")]

                    # sort by egress cost, keep up to 4 candidates
                    order = sorted(range(len(edges_list)), key=lambda i: costs[i])
                    edges_list = [edges_list[i] for i in order][:4]
                    edge_sets = [edge_sets[i] for i in order][:4]
                    cand_edges[dst] = edges_list
                    cand_edge_sets[dst] = edge_sets

                # Start with cheapest path for all partitions
                assign = {{dst: [0] * num_partitions for dst in dsts}}

                # Refinement: reroute partitions off bottleneck edges if beneficial
                best_total, worst_edge, pairs, _ = _compute_total_cost(dsts, num_partitions, assign, cand_edges, cand_edge_sets)

                max_iters = 40
                for _ in range(max_iters):
                    total, worst_edge, pairs, _ = _compute_total_cost(dsts, num_partitions, assign, cand_edges, cand_edge_sets)
                    best_total = total
                    if worst_edge is None or not pairs:
                        break

                    best_move = None
                    best_move_total = best_total

                    # Try rerouting a limited set of partitions using the worst edge
                    for (dst, p) in pairs[:30]:
                        cur_idx = assign[dst][p]
                        for alt_idx in range(len(cand_edges[dst])):
                            if alt_idx == cur_idx:
                                continue
                            # must reduce load on worst_edge
                            if worst_edge in cand_edge_sets[dst][alt_idx]:
                                continue
                            assign[dst][p] = alt_idx
                            t2, _, _, _ = _compute_total_cost(dsts, num_partitions, assign, cand_edges, cand_edge_sets)
                            if t2 + 1e-9 < best_move_total:
                                best_move_total = t2
                                best_move = (dst, p, alt_idx)
                            assign[dst][p] = cur_idx

                    if best_move is None:
                        break
                    dst, p, alt_idx = best_move
                    assign[dst][p] = alt_idx

                # Fill topology
                for dst in dsts:
                    edges_list = cand_edges[dst]
                    for p in range(num_partitions):
                        idx = assign[dst][p]
                        bc.set_dst_partition_paths(dst, p, edges_list[idx])

                return bc
            """
        ).lstrip()

        return {"code": algo_code}

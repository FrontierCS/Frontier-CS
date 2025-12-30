import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
            from collections import defaultdict
            import networkx as nx


            class BroadCastTopology:
                def __init__(self, src: str, dsts: list[str], num_partitions: int):
                    self.src = src
                    self.dsts = dsts
                    self.num_partitions = int(num_partitions)
                    self.paths = {dst: {str(i): None for i in range(self.num_partitions)} for dst in dsts}

                def append_dst_partition_path(self, dst: str, partition: int, path: list):
                    partition = str(partition)
                    if self.paths[dst][partition] is None:
                        self.paths[dst][partition] = []
                    self.paths[dst][partition].append(path)

                def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
                    partition = str(partition)
                    self.paths[dst][partition] = paths

                def set_num_partitions(self, num_partitions: int):
                    self.num_partitions = int(num_partitions)


            _EGRESS_LIMIT = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}
            _INGRESS_LIMIT = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
            _NUM_VMS_GUESS = 2.0

            _ALPHA_DEG = 0.01
            _DELTA_THR = 0.001
            _EPS = 1e-12


            def _provider(node: str) -> str:
                if not node:
                    return ""
                i = node.find(":")
                if i <= 0:
                    return node.lower()
                return node[:i].lower()


            def _node_path_from_parent(src: str, dst: str, parent: dict) -> list | None:
                if src == dst:
                    return [src]
                cur = dst
                out = []
                seen = set()
                while cur != src:
                    if cur is None or cur in seen:
                        return None
                    seen.add(cur)
                    out.append(cur)
                    cur = parent.get(cur)
                out.append(src)
                out.reverse()
                return out


            def _safe_dijkstra_path(G: nx.DiGraph, src: str, dst: str) -> list[str] | None:
                try:
                    return nx.dijkstra_path(G, src, dst, weight=lambda a, b, d: float(d.get("cost", 0.0)))
                except Exception:
                    return None


            def _paths_to_edge_list(G: nx.DiGraph, node_path: list[str]) -> list[list]:
                edges = []
                for i in range(len(node_path) - 1):
                    u = node_path[i]
                    v = node_path[i + 1]
                    if u == v:
                        continue
                    if not G.has_edge(u, v):
                        return []
                    edges.append([u, v, G[u][v]])
                return edges


            def _score_topology_by_union_edges(G: nx.DiGraph, dst_node_paths: dict[str, list[str]]) -> tuple[float, int, int]:
                edge_set = set()
                nodes = set()
                outdeg = defaultdict(int)
                for _, npath in dst_node_paths.items():
                    if not npath or len(npath) < 1:
                        continue
                    for n in npath:
                        nodes.add(n)
                    for i in range(len(npath) - 1):
                        u = npath[i]
                        v = npath[i + 1]
                        if u == v:
                            continue
                        e = (u, v)
                        if e not in edge_set:
                            edge_set.add(e)
                            outdeg[u] += 1
                total_cost = 0.0
                for (u, v) in edge_set:
                    data = G[u][v]
                    total_cost += float(data.get("cost", 0.0))
                max_outdeg = max(outdeg.values()) if outdeg else 0
                return (total_cost, len(nodes), max_outdeg)


            def _build_spt_paths(src: str, dsts: list[str], G: nx.DiGraph) -> dict[str, list[str]]:
                # Best-effort: compute each dst shortest path independently
                out = {}
                for d in dsts:
                    if d == src:
                        out[d] = [src]
                        continue
                    p = _safe_dijkstra_path(G, src, d)
                    if p is None:
                        out[d] = []
                    else:
                        out[d] = p
                return out


            def _build_greedy_steiner_parent(src: str, dsts: list[str], G: nx.DiGraph) -> dict[str, str | None]:
                tree_nodes = {src}
                parent: dict[str, str | None] = {src: None}
                outdeg_used = defaultdict(int)
                indeg_used = defaultdict(int)

                def weight(u: str, v: str, data: dict) -> float:
                    if u == v:
                        return float("inf")
                    base = float(data.get("cost", 0.0))
                    thr = float(data.get("throughput", 10.0))
                    pu = _provider(u)
                    pv = _provider(v)
                    egr = _EGRESS_LIMIT.get(pu, 10.0) * _NUM_VMS_GUESS
                    ing = _INGRESS_LIMIT.get(pv, 10.0) * _NUM_VMS_GUESS
                    deg_pen = (outdeg_used.get(u, 0) / (egr + _EPS)) + (indeg_used.get(v, 0) / (ing + _EPS))
                    thr_pen = _DELTA_THR / (thr + 0.1)
                    return base + (_ALPHA_DEG * deg_pen) + thr_pen

                remaining = set(dsts)
                remaining.discard(src)

                # Main loop
                max_iters = len(remaining) + 10
                iters = 0
                while remaining and iters < max_iters:
                    iters += 1
                    try:
                        dist, paths = nx.multi_source_dijkstra(G, list(tree_nodes), weight=weight)
                    except Exception:
                        break

                    best_dst = None
                    best_d = float("inf")
                    for d in remaining:
                        dd = dist.get(d, float("inf"))
                        if dd < best_d:
                            best_d = dd
                            best_dst = d
                    if best_dst is None or not math.isfinite(best_d):
                        break

                    node_path = paths.get(best_dst)
                    if not node_path or node_path[0] not in tree_nodes:
                        # fall back per-dst from src
                        node_path = _safe_dijkstra_path(G, src, best_dst)
                        if not node_path:
                            remaining.remove(best_dst)
                            continue

                    last_idx = 0
                    for i, n in enumerate(node_path):
                        if n in tree_nodes:
                            last_idx = i
                    suffix = node_path[last_idx:]

                    # Add suffix edges, only introducing new nodes
                    ok = True
                    for i in range(len(suffix) - 1):
                        u = suffix[i]
                        v = suffix[i + 1]
                        if u == v:
                            continue
                        if not G.has_edge(u, v):
                            ok = False
                            break
                        if v in tree_nodes:
                            # Should not happen due to last_idx, but ignore if it does
                            continue
                        parent[v] = u
                        tree_nodes.add(v)
                        outdeg_used[u] += 1
                        indeg_used[v] += 1
                    if not ok:
                        # fallback: connect dst directly
                        p2 = _safe_dijkstra_path(G, src, best_dst)
                        if p2:
                            for i in range(len(p2) - 1):
                                u = p2[i]
                                v = p2[i + 1]
                                if u == v or not G.has_edge(u, v):
                                    continue
                                if v not in parent:
                                    parent[v] = u
                                if v not in tree_nodes:
                                    tree_nodes.add(v)
                                    outdeg_used[u] += 1
                                    indeg_used[v] += 1

                    # Remove any terminals now in tree
                    for d in list(remaining):
                        if d in tree_nodes:
                            remaining.remove(d)

                # Final fallback for any remaining terminals: connect from src
                for d in list(remaining):
                    p = _safe_dijkstra_path(G, src, d)
                    if not p:
                        remaining.remove(d)
                        continue
                    for i in range(len(p) - 1):
                        u = p[i]
                        v = p[i + 1]
                        if u == v or not G.has_edge(u, v):
                            continue
                        if v not in parent:
                            parent[v] = u
                        if v not in tree_nodes:
                            tree_nodes.add(v)
                    remaining.remove(d)

                return parent


            def _build_paths_from_parent(src: str, dsts: list[str], parent: dict, G: nx.DiGraph) -> dict[str, list[str]]:
                out = {}
                for d in dsts:
                    if d == src:
                        out[d] = [src]
                        continue
                    np = _node_path_from_parent(src, d, parent)
                    if not np:
                        np = _safe_dijkstra_path(G, src, d)
                        out[d] = np if np else []
                    else:
                        # Validate edges exist
                        valid = True
                        for i in range(len(np) - 1):
                            if not G.has_edge(np[i], np[i + 1]):
                                valid = False
                                break
                        if not valid:
                            np2 = _safe_dijkstra_path(G, src, d)
                            out[d] = np2 if np2 else []
                        else:
                            out[d] = np
                return out


            def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
                num_partitions = int(num_partitions)
                bc = BroadCastTopology(src, dsts, num_partitions)

                if num_partitions <= 0:
                    bc.set_num_partitions(0)
                    return bc

                # Candidate A: shortest paths from src
                spt_paths = _build_spt_paths(src, dsts, G)
                spt_score = _score_topology_by_union_edges(G, spt_paths)

                # Candidate B: greedy directed steiner-like arborescence
                parent = _build_greedy_steiner_parent(src, dsts, G)
                greedy_paths = _build_paths_from_parent(src, dsts, parent, G)
                greedy_score = _score_topology_by_union_edges(G, greedy_paths)

                use_greedy = greedy_score < spt_score
                final_paths = greedy_paths if use_greedy else spt_paths

                # Populate topology
                for dst in dsts:
                    node_path = final_paths.get(dst)
                    if not node_path:
                        node_path = _safe_dijkstra_path(G, src, dst) or [src, dst] if G.has_edge(src, dst) else [src]
                    edge_list = _paths_to_edge_list(G, node_path)
                    if not edge_list and dst != src:
                        node_path2 = _safe_dijkstra_path(G, src, dst)
                        if node_path2:
                            edge_list = _paths_to_edge_list(G, node_path2)
                    # Ensure non-None paths for all partitions
                    for p in range(num_partitions):
                        bc.set_dst_partition_paths(dst, p, list(edge_list))
                return bc
            """
        )
        return {"code": code}
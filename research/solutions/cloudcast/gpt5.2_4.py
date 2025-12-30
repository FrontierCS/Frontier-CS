import json
import textwrap
from typing import Dict, Any


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r"""
            import math
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


            def _provider(node: str) -> str:
                i = node.find(":")
                if i == -1:
                    return node.lower()
                return node[:i].lower()


            class _State:
                __slots__ = (
                    "G",
                    "edge_load",
                    "used_edges",
                    "out_adj",
                    "in_adj",
                    "out_deg",
                    "in_deg",
                    "node_edge_count",
                    "used_nodes",
                )

                def __init__(self, G: nx.DiGraph):
                    self.G = G
                    self.edge_load = {}          # (u,v) -> int partitions across all (dst,part)
                    self.used_edges = set()      # keys in edge_load
                    self.out_adj = {}            # u -> set(v)
                    self.in_adj = {}             # v -> set(u)
                    self.out_deg = {}            # u -> len(out_adj[u])
                    self.in_deg = {}             # v -> len(in_adj[v])
                    self.node_edge_count = {}    # node -> number of incident used edges (distinct)
                    self.used_nodes = set()      # nodes with node_edge_count>0

                def _do_used_edge_add(self, key):
                    self.used_edges.add(key)

                def _do_used_edge_remove(self, key):
                    self.used_edges.discard(key)

                def _do_node_inc(self, n):
                    prev = self.node_edge_count.get(n, 0)
                    newv = prev + 1
                    self.node_edge_count[n] = newv
                    if prev == 0:
                        self.used_nodes.add(n)

                def _do_node_dec(self, n):
                    prev = self.node_edge_count.get(n, 0)
                    if prev <= 1:
                        if prev == 1:
                            self.node_edge_count.pop(n, None)
                        self.used_nodes.discard(n)
                    else:
                        self.node_edge_count[n] = prev - 1

                def _do_out_add(self, u, v):
                    s = self.out_adj.get(u)
                    if s is None:
                        s = set()
                        self.out_adj[u] = s
                        self.out_deg[u] = 0
                    if v not in s:
                        s.add(v)
                        self.out_deg[u] = self.out_deg.get(u, 0) + 1

                def _do_out_remove(self, u, v):
                    s = self.out_adj.get(u)
                    if not s:
                        return
                    if v in s:
                        s.remove(v)
                        d = self.out_deg.get(u, 0) - 1
                        if d <= 0:
                            self.out_deg.pop(u, None)
                            self.out_adj.pop(u, None)
                        else:
                            self.out_deg[u] = d

                def _do_in_add(self, v, u):
                    s = self.in_adj.get(v)
                    if s is None:
                        s = set()
                        self.in_adj[v] = s
                        self.in_deg[v] = 0
                    if u not in s:
                        s.add(u)
                        self.in_deg[v] = self.in_deg.get(v, 0) + 1

                def _do_in_remove(self, v, u):
                    s = self.in_adj.get(v)
                    if not s:
                        return
                    if u in s:
                        s.remove(u)
                        d = self.in_deg.get(v, 0) - 1
                        if d <= 0:
                            self.in_deg.pop(v, None)
                            self.in_adj.pop(v, None)
                        else:
                            self.in_deg[v] = d

                def _apply_op(self, op):
                    t = op[0]
                    if t == "used_edge_add":
                        self._do_used_edge_add(op[1])
                    elif t == "used_edge_remove":
                        self._do_used_edge_remove(op[1])
                    elif t == "out_add":
                        self._do_out_add(op[1], op[2])
                    elif t == "out_remove":
                        self._do_out_remove(op[1], op[2])
                    elif t == "in_add":
                        self._do_in_add(op[1], op[2])
                    elif t == "in_remove":
                        self._do_in_remove(op[1], op[2])
                    elif t == "node_inc":
                        self._do_node_inc(op[1])
                    elif t == "node_dec":
                        self._do_node_dec(op[1])
                    else:
                        raise RuntimeError("unknown op")

                def _invert_op(self, op):
                    t = op[0]
                    if t == "used_edge_add":
                        return ("used_edge_remove", op[1])
                    if t == "used_edge_remove":
                        return ("used_edge_add", op[1])
                    if t == "out_add":
                        return ("out_remove", op[1], op[2])
                    if t == "out_remove":
                        return ("out_add", op[1], op[2])
                    if t == "in_add":
                        return ("in_remove", op[1], op[2])
                    if t == "in_remove":
                        return ("in_add", op[1], op[2])
                    if t == "node_inc":
                        return ("node_dec", op[1])
                    if t == "node_dec":
                        return ("node_inc", op[1])
                    raise RuntimeError("unknown op to invert")

                def apply_path_temp(self, edges_uv, delta: int):
                    # edges_uv: list[(u,v)] along the path
                    # delta: +1 or -1 partition-path usage
                    changes = []
                    el = self.edge_load
                    for (u, v) in edges_uv:
                        key = (u, v)
                        prev = el.get(key, 0)
                        new = prev + delta
                        if new < 0:
                            # invalid; keep state unchanged
                            raise RuntimeError("edge load would become negative")

                        changes.append(("load", key, prev))

                        if prev == 0 and new > 0:
                            # edge becomes present
                            ops = (
                                ("used_edge_add", key),
                                ("out_add", u, v),
                                ("in_add", v, u),
                                ("node_inc", u),
                                ("node_inc", v),
                            )
                            for op in ops:
                                self._apply_op(op)
                                changes.append(("op", op))
                            el[key] = new
                        elif prev > 0 and new == 0:
                            # edge removed
                            ops = (
                                ("used_edge_remove", key),
                                ("out_remove", u, v),
                                ("in_remove", v, u),
                                ("node_dec", u),
                                ("node_dec", v),
                            )
                            for op in ops:
                                self._apply_op(op)
                                changes.append(("op", op))
                            el.pop(key, None)
                        else:
                            if new == 0:
                                el.pop(key, None)
                            else:
                                el[key] = new
                    return changes

                def revert(self, changes):
                    el = self.edge_load
                    for ch in reversed(changes):
                        if ch[0] == "op":
                            inv = self._invert_op(ch[1])
                            self._apply_op(inv)
                        elif ch[0] == "load":
                            key, prev = ch[1], ch[2]
                            if prev <= 0:
                                el.pop(key, None)
                            else:
                                el[key] = prev
                        else:
                            raise RuntimeError("unknown change kind")


            def _edge_cost(G: nx.DiGraph, u: str, v: str) -> float:
                d = G[u][v]
                c = d.get("cost", 0.0)
                try:
                    return float(c)
                except Exception:
                    return 0.0


            def _edge_thr(G: nx.DiGraph, u: str, v: str) -> float:
                d = G[u][v]
                t = d.get("throughput", 1.0)
                try:
                    return float(t)
                except Exception:
                    return 1.0


            def _path_to_edges(nodes):
                return [(nodes[i], nodes[i + 1]) for i in range(len(nodes) - 1)]


            def _path_cost(G, nodes):
                s = 0.0
                for i in range(len(nodes) - 1):
                    s += _edge_cost(G, nodes[i], nodes[i + 1])
                return s


            def _safe_dijkstra_path(G, src, dst, weight):
                try:
                    return nx.dijkstra_path(G, src, dst, weight=weight)
                except Exception:
                    return None


            def _compute_candidate_paths(G: nx.DiGraph, src: str, dst: str, max_paths: int = 6):
                if src == dst:
                    return [[src]]

                cand = []
                seen = set()

                def add_path(nodes):
                    if not nodes or nodes[0] != src or nodes[-1] != dst:
                        return
                    t = tuple(nodes)
                    if t in seen:
                        return
                    seen.add(t)
                    cand.append(nodes)

                # baseline by cost
                p0 = _safe_dijkstra_path(G, src, dst, "cost")
                if p0 is not None:
                    add_path(p0)

                # a few k-shortest by cost (often gives good diversity)
                try:
                    gen = nx.shortest_simple_paths(G, src, dst, weight="cost")
                    for _ in range(3):
                        add_path(next(gen))
                        if len(cand) >= max_paths:
                            break
                except Exception:
                    pass

                # throughput-aware weights
                eps = 1e-9
                def w_factory(alpha, hop):
                    def w(u, v, d):
                        c = d.get("cost", 0.0)
                        t = d.get("throughput", 1.0)
                        try:
                            c = float(c)
                        except Exception:
                            c = 0.0
                        try:
                            t = float(t)
                        except Exception:
                            t = 1.0
                        return c + alpha / (t + eps) + hop
                    return w

                for alpha, hop in ((0.02, 0.0005), (0.05, 0.0005), (0.1, 0.0005), (0.2, 0.0008)):
                    if len(cand) >= max_paths:
                        break
                    pw = _safe_dijkstra_path(G, src, dst, w_factory(alpha, hop))
                    if pw is not None:
                        add_path(pw)

                # if still empty, try unweighted
                if not cand:
                    try:
                        add_path(nx.shortest_path(G, src, dst))
                    except Exception:
                        pass

                # prune by cost to keep only best few
                if len(cand) > max_paths:
                    cand.sort(key=lambda nodes: (_path_cost(G, nodes), len(nodes)))
                    cand = cand[:max_paths]

                return cand


            def _compute_total_cost_per_partition_size(
                state: _State,
                ingress_limit_map,
                egress_limit_map,
                num_vms: int,
                instance_rate_per_hour: float,
            ):
                # total_per_s = sum(load*c_e) + |V|*gamma*max(load/f_e)
                # gamma = n_vms * (rate/3600) * 8
                gamma = (float(num_vms) * float(instance_rate_per_hour) / 3600.0) * 8.0

                egress_sum = 0.0
                max_metric = 0.0

                G = state.G
                out_deg = state.out_deg
                in_deg = state.in_deg
                edge_load = state.edge_load

                for (u, v) in state.used_edges:
                    load = edge_load.get((u, v), 0)
                    if load <= 0:
                        continue

                    d = G[u][v]
                    c = d.get("cost", 0.0)
                    thr = d.get("throughput", 1.0)
                    try:
                        c = float(c)
                    except Exception:
                        c = 0.0
                    try:
                        thr = float(thr)
                    except Exception:
                        thr = 1.0

                    egress_sum += load * c

                    pu = _provider(u)
                    pv = _provider(v)
                    e_lim = float(egress_limit_map.get(pu, 5.0)) * float(num_vms)
                    i_lim = float(ingress_limit_map.get(pv, 10.0)) * float(num_vms)

                    od = out_deg.get(u, 1)
                    idg = in_deg.get(v, 1)

                    if od <= 0:
                        od = 1
                    if idg <= 0:
                        idg = 1

                    share_out = e_lim / float(od)
                    share_in = i_lim / float(idg)

                    f_e = thr
                    if share_out < f_e:
                        f_e = share_out
                    if share_in < f_e:
                        f_e = share_in
                    if f_e <= 1e-12:
                        f_e = 1e-12

                    metric = float(load) / f_e
                    if metric > max_metric:
                        max_metric = metric

                inst = gamma * float(len(state.used_nodes)) * max_metric
                return egress_sum + inst, egress_sum, inst, max_metric


            def _bottleneck_edge(
                state: _State,
                ingress_limit_map,
                egress_limit_map,
                num_vms: int,
            ):
                G = state.G
                out_deg = state.out_deg
                in_deg = state.in_deg
                edge_load = state.edge_load

                best_key = None
                best_metric = -1.0

                for (u, v) in state.used_edges:
                    load = edge_load.get((u, v), 0)
                    if load <= 0:
                        continue

                    thr = _edge_thr(G, u, v)

                    pu = _provider(u)
                    pv = _provider(v)
                    e_lim = float(egress_limit_map.get(pu, 5.0)) * float(num_vms)
                    i_lim = float(ingress_limit_map.get(pv, 10.0)) * float(num_vms)

                    od = out_deg.get(u, 1)
                    idg = in_deg.get(v, 1)

                    if od <= 0:
                        od = 1
                    if idg <= 0:
                        idg = 1

                    share_out = e_lim / float(od)
                    share_in = i_lim / float(idg)

                    f_e = thr
                    if share_out < f_e:
                        f_e = share_out
                    if share_in < f_e:
                        f_e = share_in
                    if f_e <= 1e-12:
                        f_e = 1e-12

                    metric = float(load) / f_e
                    if metric > best_metric:
                        best_metric = metric
                        best_key = (u, v)

                return best_key, best_metric


            def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
                num_partitions = int(num_partitions)
                bc_topology = BroadCastTopology(src, dsts, num_partitions)

                # Defaults per statement; allow overrides via G.graph if present
                ingress_limit_map = G.graph.get("ingress_limit", {"aws": 10.0, "gcp": 16.0, "azure": 16.0})
                egress_limit_map = G.graph.get("egress_limit", {"aws": 5.0, "gcp": 7.0, "azure": 16.0})
                num_vms = int(G.graph.get("num_vms", 2))
                instance_rate_per_hour = float(G.graph.get("instance_rate", 0.54))

                # Candidate paths per destination
                cand_nodes = {}
                cand_edges = {}
                cand_cost = {}
                for dst in dsts:
                    cpaths = _compute_candidate_paths(G, src, dst, max_paths=6)
                    if not cpaths:
                        # As a last resort, try any path; if none exists, raise
                        cpaths = [_safe_dijkstra_path(G, src, dst, None)]
                        if not cpaths or cpaths[0] is None:
                            raise RuntimeError(f"No path from {src} to {dst}")
                    cand_nodes[dst] = cpaths
                    edges_list = []
                    costs_list = []
                    for nodes in cpaths:
                        e = _path_to_edges(nodes)
                        edges_list.append(e)
                        costs_list.append(_path_cost(G, nodes))
                    cand_edges[dst] = edges_list
                    cand_cost[dst] = costs_list

                # Commodity list: (id, dst, partition)
                commodities = []
                cid = 0
                for dst in dsts:
                    for p in range(num_partitions):
                        commodities.append((cid, dst, p))
                        cid += 1

                # Order: route "harder" ones first (higher min cost, fewer candidates)
                def _sort_key(item):
                    _, dst, _ = item
                    return (len(cand_edges[dst]), -min(cand_cost[dst]) if cand_cost[dst] else 0.0)

                commodities.sort(key=_sort_key)

                state = _State(G)

                # edge -> set(commodity_id)
                edge_users = {}
                # commodity_id -> edges list
                commodity_path_edges = [None] * len(commodities)
                commodity_dst = [None] * len(commodities)
                commodity_part = [None] * len(commodities)

                # Greedy assignment minimizing global objective
                for (cid, dst, part) in commodities:
                    commodity_dst[cid] = dst
                    commodity_part[cid] = part

                    best_total = None
                    best_idx = 0
                    best_edges = None

                    cands = cand_edges[dst]
                    # prefer lower base cost as weak tie-breaker
                    for idx, edges_uv in enumerate(cands):
                        try:
                            ch = state.apply_path_temp(edges_uv, +1)
                        except Exception:
                            continue
                        total, _, _, _ = _compute_total_cost_per_partition_size(
                            state, ingress_limit_map, egress_limit_map, num_vms, instance_rate_per_hour
                        )
                        state.revert(ch)

                        if best_total is None or total < best_total - 1e-12 or (abs(total - best_total) <= 1e-12 and cand_cost[dst][idx] < cand_cost[dst][best_idx]):
                            best_total = total
                            best_idx = idx
                            best_edges = edges_uv

                    if best_edges is None:
                        # fallback: the first candidate must exist
                        best_edges = cands[0]

                    state.apply_path_temp(best_edges, +1)

                    commodity_path_edges[cid] = best_edges
                    for e in best_edges:
                        s = edge_users.get(e)
                        if s is None:
                            s = set()
                            edge_users[e] = s
                        s.add(cid)

                # Local improvement: reroute users of bottleneck edge
                cur_total, _, _, _ = _compute_total_cost_per_partition_size(
                    state, ingress_limit_map, egress_limit_map, num_vms, instance_rate_per_hour
                )

                max_outer = 30
                for _ in range(max_outer):
                    b_edge, _m = _bottleneck_edge(state, ingress_limit_map, egress_limit_map, num_vms)
                    if b_edge is None:
                        break
                    users = list(edge_users.get(b_edge, ()))
                    if not users:
                        break

                    # Try a limited subset of users for speed
                    if len(users) > 25:
                        # deterministic sampling: sort by path length descending
                        users.sort(key=lambda x: -len(commodity_path_edges[x]))
                        users = users[:25]

                    best_improve = 0.0
                    best_move = None  # (cid, new_edges)

                    for cid_u in users:
                        dst = commodity_dst[cid_u]
                        old_edges = commodity_path_edges[cid_u]
                        if not old_edges:
                            continue
                        cands = cand_edges[dst]
                        if len(cands) <= 1:
                            continue

                        for edges_uv in cands:
                            if edges_uv == old_edges:
                                continue

                            try:
                                ch1 = state.apply_path_temp(old_edges, -1)
                                ch2 = state.apply_path_temp(edges_uv, +1)
                            except Exception:
                                # revert what was applied
                                try:
                                    state.revert(ch2)
                                except Exception:
                                    pass
                                try:
                                    state.revert(ch1)
                                except Exception:
                                    pass
                                continue

                            total, _, _, _ = _compute_total_cost_per_partition_size(
                                state, ingress_limit_map, egress_limit_map, num_vms, instance_rate_per_hour
                            )
                            state.revert(ch2)
                            state.revert(ch1)

                            improve = cur_total - total
                            if improve > best_improve + 1e-12:
                                best_improve = improve
                                best_move = (cid_u, edges_uv)

                    if best_move is None:
                        break

                    cid_u, new_edges = best_move
                    dst = commodity_dst[cid_u]
                    old_edges = commodity_path_edges[cid_u]

                    # Apply permanently
                    state.apply_path_temp(old_edges, -1)
                    state.apply_path_temp(new_edges, +1)

                    # Update edge_users
                    for e in old_edges:
                        s = edge_users.get(e)
                        if s is not None:
                            s.discard(cid_u)
                            if not s:
                                edge_users.pop(e, None)
                    for e in new_edges:
                        s = edge_users.get(e)
                        if s is None:
                            s = set()
                            edge_users[e] = s
                        s.add(cid_u)

                    commodity_path_edges[cid_u] = new_edges

                    cur_total, _, _, _ = _compute_total_cost_per_partition_size(
                        state, ingress_limit_map, egress_limit_map, num_vms, instance_rate_per_hour
                    )

                # Emit topology
                # Map commodity ids to dst/partition from stored arrays
                for cid_u in range(len(commodity_path_edges)):
                    dst = commodity_dst[cid_u]
                    part = commodity_part[cid_u]
                    edges_uv = commodity_path_edges[cid_u]
                    if edges_uv is None:
                        edges_uv = []

                    edges_out = []
                    for (u, v) in edges_uv:
                        if u == v:
                            continue
                        edges_out.append([u, v, G[u][v]])
                    bc_topology.set_dst_partition_paths(dst, part, edges_out)

                return bc_topology
            """
        ).strip() + "\n"
        return {"code": code}
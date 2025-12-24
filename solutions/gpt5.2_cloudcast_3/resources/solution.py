import json
import os
import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        code = textwrap.dedent(
            r'''
            import math
            import itertools
            import heapq
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


            def _provider(node: str) -> str:
                i = node.find(':')
                if i <= 0:
                    return ""
                return node[:i].lower()


            def _make_weight(cost_w: float, thru_w: float, cross_penalty: float, prefer_provider: str = ""):
                if not prefer_provider:
                    def w(u, v, d):
                        c = float(d.get("cost", 0.0))
                        t = float(d.get("throughput", 1e-9))
                        if t <= 0:
                            t = 1e-9
                        return cost_w * c + thru_w * (1.0 / t)
                    return w

                def w(u, v, d):
                    c = float(d.get("cost", 0.0))
                    t = float(d.get("throughput", 1e-9))
                    if t <= 0:
                        t = 1e-9
                    pen = 0.0
                    if _provider(u) != prefer_provider or _provider(v) != prefer_provider:
                        pen = cross_penalty
                    return cost_w * c + thru_w * (1.0 / t) + pen
                return w


            def _dijkstra_path_edges(G: nx.DiGraph, src: str, dst: str, weight_func):
                if src == dst:
                    return []
                dist = {src: 0.0}
                pred = {}
                h = [(0.0, src)]
                INF = float("inf")

                while h:
                    d, u = heapq.heappop(h)
                    if d != dist.get(u):
                        continue
                    if u == dst:
                        break
                    adj = G[u]
                    for v, edata in adj.items():
                        nd = d + weight_func(u, v, edata)
                        if nd < dist.get(v, INF):
                            dist[v] = nd
                            pred[v] = u
                            heapq.heappush(h, (nd, v))

                if dst not in dist:
                    raise nx.NetworkXNoPath

                edges = []
                cur = dst
                while cur != src:
                    pu = pred.get(cur)
                    if pu is None:
                        raise nx.NetworkXNoPath
                    edges.append((pu, cur))
                    cur = pu
                edges.reverse()
                return edges


            def _find_nearest_terminal(G: nx.DiGraph, sources_set: set, terminals_set: set, weight_func):
                # Multi-source dijkstra; stop at first popped terminal (nearest)
                dist = {}
                pred = {}
                h = []
                for s in sources_set:
                    dist[s] = 0.0
                    heapq.heappush(h, (0.0, s))
                INF = float("inf")
                while h:
                    d, u = heapq.heappop(h)
                    if d != dist.get(u):
                        continue
                    if u in terminals_set:
                        return u, pred
                    adj = G[u]
                    for v, edata in adj.items():
                        nd = d + weight_func(u, v, edata)
                        if nd < dist.get(v, INF):
                            dist[v] = nd
                            pred[v] = u
                            heapq.heappush(h, (nd, v))
                return None, pred


            def _build_greedy_arborescence_paths(G: nx.DiGraph, root: str, terminals: list[str], weight_func):
                # Returns:
                # - per_terminal_edges: dict[terminal] = list[(u,v)]
                # - union_edges: set[(u,v)]
                terminals_set = set(terminals)
                if root in terminals_set:
                    terminals_set.remove(root)

                tree_nodes = {root}
                parent = {root: None}
                remaining = set(terminals_set)
                union_edges = set()

                # Greedily connect nearest remaining terminal to current tree
                while remaining:
                    t, pred = _find_nearest_terminal(G, tree_nodes, remaining, weight_func)
                    if t is None:
                        break

                    # Backtrack from t to first node in tree_nodes
                    rev_edges = []
                    cur = t
                    while cur not in tree_nodes:
                        pu = pred.get(cur)
                        if pu is None:
                            break
                        rev_edges.append((pu, cur))
                        cur = pu
                    if cur not in tree_nodes:
                        # Shouldn't happen if pred chain fails; fall back later
                        remaining.remove(t)
                        continue

                    # Add path edges from tree to t
                    for u, v in reversed(rev_edges):
                        union_edges.add((u, v))
                        if v not in tree_nodes:
                            tree_nodes.add(v)
                            parent[v] = u
                        # If v already in tree, we still keep union edge but don't overwrite parent
                    remaining.remove(t)

                per_term_edges = {}

                # Reconstruct edges via parent (for those in arborescence)
                for term in terminals:
                    if term == root:
                        per_term_edges[term] = []
                        continue
                    if term in parent:
                        # walk back to root
                        seq = []
                        cur = term
                        seen = set()
                        while cur != root:
                            if cur in seen:
                                seq = None
                                break
                            seen.add(cur)
                            pu = parent.get(cur)
                            if pu is None:
                                seq = None
                                break
                            seq.append((pu, cur))
                            cur = pu
                        if seq is not None:
                            seq.reverse()
                            per_term_edges[term] = seq
                            for e in seq:
                                union_edges.add(e)
                            continue

                    # Fallback: direct shortest path
                    try:
                        seq = _dijkstra_path_edges(G, root, term, weight_func)
                        per_term_edges[term] = seq
                        for e in seq:
                            union_edges.add(e)
                    except nx.NetworkXNoPath:
                        per_term_edges[term] = None

                return per_term_edges, union_edges


            def _bits_for_mod_class(num_partitions: int, k: int, idx: int):
                if k <= 1:
                    return (1 << num_partitions) - 1
                if k == 2:
                    bits = 0
                    if idx == 0:
                        for p in range(0, num_partitions, 2):
                            bits |= (1 << p)
                    else:
                        for p in range(1, num_partitions, 2):
                            bits |= (1 << p)
                    return bits
                # General k (not used in current search, but kept safe)
                bits = 0
                for p in range(num_partitions):
                    if (p % k) == idx:
                        bits |= (1 << p)
                return bits


            def _evaluate_selection(
                G: nx.DiGraph,
                src: str,
                dsts: list[str],
                num_partitions: int,
                src_provider: str,
                provider_to_dsts: dict,
                selection_gateways: dict,          # P -> [g] or [g1,g2]
                src_tree_union_edges: set,
                src_tree_edges_per_dst: dict,
                src_to_g_edges_set: dict,          # g -> set[(u,v)]
                prov_g_tree_union_edges: dict,     # (P,g) -> set[(u,v)]
                ingress_limit: dict,
                egress_limit: dict,
                n_vm: int,
                inst_rate: float
            ):
                np = num_partitions
                if np <= 0:
                    return float("inf")

                all_bits = (1 << np) - 1
                edge_mask = defaultdict(int)

                # Include src-provider internal tree for all partitions
                if src_tree_union_edges:
                    for e in src_tree_union_edges:
                        edge_mask[e] |= all_bits

                # Include other providers by gateway assignment (by partition modulo)
                for P, dstsP in provider_to_dsts.items():
                    if not dstsP:
                        continue
                    if P == src_provider:
                        continue
                    gL = selection_gateways.get(P)
                    if not gL:
                        continue
                    k = len(gL)
                    for idx, g in enumerate(gL):
                        bits = _bits_for_mod_class(np, k, idx)
                        if bits == 0:
                            continue
                        sset = src_to_g_edges_set.get(g)
                        if sset:
                            for e in sset:
                                edge_mask[e] |= bits
                        tset = prov_g_tree_union_edges.get((P, g))
                        if tset:
                            for e in tset:
                                edge_mask[e] |= bits

                if not edge_mask:
                    return float("inf")

                used_edges = list(edge_mask.keys())

                # Degrees for node-share constraints
                out_deg = defaultdict(int)
                in_deg = defaultdict(int)
                nodes = set([src])
                for d in dsts:
                    nodes.add(d)

                for u, v in used_edges:
                    out_deg[u] += 1
                    in_deg[v] += 1
                    nodes.add(u)
                    nodes.add(v)

                # Per-node shares
                e_share = {}
                i_share = {}
                INF = 1e30
                for u, deg in out_deg.items():
                    prov = _provider(u)
                    lim = egress_limit.get(prov, INF) * n_vm
                    if deg > 0 and lim < INF:
                        e_share[u] = lim / deg
                    else:
                        e_share[u] = INF
                for v, deg in in_deg.items():
                    prov = _provider(v)
                    lim = ingress_limit.get(prov, INF) * n_vm
                    if deg > 0 and lim < INF:
                        i_share[v] = lim / deg
                    else:
                        i_share[v] = INF

                # Objective components normalized per GB
                # egress_norm = sum_e frac_e * cost_e
                # time_norm = max_e frac_e * 8 / f_e
                egress_norm = 0.0
                time_norm = 0.0
                inv_np = 1.0 / np

                for (u, v) in used_edges:
                    d = G[u][v]
                    cost = float(d.get("cost", 0.0))
                    tp = float(d.get("throughput", 1e-9))
                    if tp <= 0:
                        tp = 1e-9
                    f = tp
                    es = e_share.get(u, INF)
                    if es < f:
                        f = es
                    ins = i_share.get(v, INF)
                    if ins < f:
                        f = ins
                    if f <= 0:
                        f = 1e-9

                    pe = edge_mask[(u, v)].bit_count()
                    if pe <= 0:
                        continue
                    frac = pe * inv_np
                    egress_norm += frac * cost
                    t = frac * 8.0 / f
                    if t > time_norm:
                        time_norm = t

                K = (n_vm * inst_rate) / 3600.0
                instance_norm = len(nodes) * K * time_norm
                return egress_norm + instance_norm


            def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
                np = int(num_partitions)
                bc = BroadCastTopology(src, dsts, np)
                if np <= 0:
                    return bc

                # Hardcoded limits as per prompt (assumed evaluator defaults)
                ingress_limit = {"aws": 10.0, "gcp": 16.0, "azure": 16.0}
                egress_limit = {"aws": 5.0, "gcp": 7.0, "azure": 16.0}
                n_vm = 2
                inst_rate = 0.54

                src_prov = _provider(src)

                provider_to_dsts = defaultdict(list)
                for d in dsts:
                    provider_to_dsts[_provider(d)].append(d)

                # Weights
                # Hybrid for actual routing
                THRU_W = 0.06
                COST_W = 1.0
                CROSS_PENALTY = 0.03
                weight_global = _make_weight(COST_W, THRU_W, 0.0, "")
                weight_internal_cache = {}

                def internal_weight(P: str):
                    wf = weight_internal_cache.get(P)
                    if wf is not None:
                        return wf
                    wf = _make_weight(COST_W, THRU_W, CROSS_PENALTY, P)
                    weight_internal_cache[P] = wf
                    return wf

                # Build src-provider internal tree once (if needed)
                src_tree_per_dst = {}
                src_tree_union_edges = set()
                dsts_src = provider_to_dsts.get(src_prov, [])
                if dsts_src:
                    src_tree_per_dst, src_tree_union_edges = _build_greedy_arborescence_paths(
                        G, src, dsts_src, internal_weight(src_prov)
                    )

                # Candidate gateways and precomputed paths/trees for other providers
                # Precompute cost-only distances from src for candidate ranking
                try:
                    dist_cost_from_src = nx.single_source_dijkstra_path_length(G, src, weight="cost")
                except Exception:
                    dist_cost_from_src = {src: 0.0}

                providers_other = [p for p in provider_to_dsts.keys() if p != src_prov]
                options = {}  # P -> list of gateway lists (each list length 1 or 2)
                provider_candidates = {}  # P -> list[g]
                src_to_g_edges = {}  # g -> list[(u,v)]
                src_to_g_edges_set = {}  # g -> set[(u,v)]
                prov_g_tree_per_dst = {}  # (P,g) -> dict[dst] -> list[(u,v)]
                prov_g_tree_union_edges = {}  # (P,g) -> set[(u,v)]

                for P in providers_other:
                    dstsP = provider_to_dsts.get(P, [])
                    if not dstsP:
                        options[P] = []
                        continue

                    # Candidate pool: all dsts + a few nodes in provider with small dist from src
                    prov_nodes = [n for n in G.nodes if _provider(n) == P]
                    cand_pool = set(dstsP)

                    # Add a few closest nodes to src in this provider
                    ranked = []
                    for n in prov_nodes:
                        dc = dist_cost_from_src.get(n)
                        if dc is not None:
                            ranked.append((dc, n))
                    ranked.sort()
                    for _, n in ranked[:8]:
                        cand_pool.add(n)

                    # Score candidates by dist(src->g) + 0.5 * avg(dist(g->dst))
                    scored = []
                    for g in cand_pool:
                        dc = dist_cost_from_src.get(g)
                        if dc is None:
                            continue
                        try:
                            dist_from_g = nx.single_source_dijkstra_path_length(G, g, weight="cost")
                        except Exception:
                            dist_from_g = {}
                        s = 0.0
                        ok = 0
                        for d in dstsP:
                            dd = dist_from_g.get(d)
                            if dd is not None:
                                s += dd
                                ok += 1
                        if ok == 0:
                            avg = 1e9
                        else:
                            avg = s / ok
                        scored.append((dc + 0.5 * avg, dc, g))
                    scored.sort()
                    cands = [g for _, __, g in scored[:6]]
                    if not cands:
                        # Fallback: use destinations as gateways if reachable
                        for d in dstsP:
                            if d in dist_cost_from_src:
                                cands.append(d)
                                if len(cands) >= 3:
                                    break
                    if not cands:
                        options[P] = []
                        continue

                    provider_candidates[P] = cands

                    # Precompute src->g path edges and trees g->dstsP
                    for g in cands:
                        if g not in src_to_g_edges:
                            try:
                                epath = _dijkstra_path_edges(G, src, g, weight_global)
                            except nx.NetworkXNoPath:
                                epath = None
                            src_to_g_edges[g] = epath
                            src_to_g_edges_set[g] = set(epath) if epath else set()

                        key = (P, g)
                        if key not in prov_g_tree_union_edges:
                            per_dst, union_e = _build_greedy_arborescence_paths(G, g, dstsP, internal_weight(P))
                            prov_g_tree_per_dst[key] = per_dst
                            prov_g_tree_union_edges[key] = union_e

                    # Create options: a few single gateways + a few pairs
                    singles = [[g] for g in cands[:3]]
                    pairs = []
                    base_for_pairs = cands[:4] if len(cands) >= 4 else cands
                    if len(base_for_pairs) >= 2:
                        for i in range(len(base_for_pairs)):
                            for j in range(i + 1, len(base_for_pairs)):
                                pairs.append([base_for_pairs[i], base_for_pairs[j]])
                    options[P] = singles + pairs

                # If some provider has no viable options, fall back later
                for P in providers_other:
                    if not options.get(P):
                        # We'll handle by routing directly per destination for all partitions
                        options[P] = [None]

                # Evaluate combinations
                providers_for_product = [P for P in providers_other if P in options]
                option_lists = [options[P] for P in providers_for_product]

                best_sel = {}
                best_score = float("inf")

                # Baseline selection: first option in each
                if option_lists:
                    for combo in itertools.product(*option_lists):
                        sel = {}
                        feasible = True
                        for P, opt in zip(providers_for_product, combo):
                            if opt is None:
                                # handled in fallback, but treat as not feasible for optimizer
                                feasible = False
                                break
                            sel[P] = opt
                        if not feasible:
                            continue
                        score = _evaluate_selection(
                            G=G,
                            src=src,
                            dsts=dsts,
                            num_partitions=np,
                            src_provider=src_prov,
                            provider_to_dsts=provider_to_dsts,
                            selection_gateways=sel,
                            src_tree_union_edges=src_tree_union_edges,
                            src_tree_edges_per_dst=src_tree_per_dst,
                            src_to_g_edges_set=src_to_g_edges_set,
                            prov_g_tree_union_edges=prov_g_tree_union_edges,
                            ingress_limit=ingress_limit,
                            egress_limit=egress_limit,
                            n_vm=n_vm,
                            inst_rate=inst_rate
                        )
                        if score < best_score:
                            best_score = score
                            best_sel = sel
                else:
                    best_sel = {}
                    best_score = _evaluate_selection(
                        G=G,
                        src=src,
                        dsts=dsts,
                        num_partitions=np,
                        src_provider=src_prov,
                        provider_to_dsts=provider_to_dsts,
                        selection_gateways={},
                        src_tree_union_edges=src_tree_union_edges,
                        src_tree_edges_per_dst=src_tree_per_dst,
                        src_to_g_edges_set=src_to_g_edges_set,
                        prov_g_tree_union_edges=prov_g_tree_union_edges,
                        ingress_limit=ingress_limit,
                        egress_limit=egress_limit,
                        n_vm=n_vm,
                        inst_rate=inst_rate
                    )

                # Finalize: if any provider had no feasible selection, use a direct-per-destination route
                # This guarantees correctness even if our optimizer couldn't find gateway paths.
                # Build per-destination fallback paths:
                fallback_paths = {}  # (dst) -> list[(u,v)] shortest path by cost
                def cost_only_weight(u, v, d):
                    return float(d.get("cost", 0.0))

                for d in dsts:
                    try:
                        edges = _dijkstra_path_edges(G, src, d, cost_only_weight)
                    except nx.NetworkXNoPath:
                        edges = []
                    fallback_paths[d] = edges

                # Helpers to convert tuple-edges to BroadCastTopology edge objects
                def edges_to_obj_list(edges_tuples):
                    if not edges_tuples:
                        return []
                    out = []
                    for u, v in edges_tuples:
                        out.append([u, v, G[u][v]])
                    return out

                # Build and assign paths
                for d in dsts:
                    P = _provider(d)
                    if P == src_prov and dsts_src:
                        path_edges = src_tree_per_dst.get(d)
                        if path_edges is None:
                            path_edges = fallback_paths.get(d, [])
                        obj = edges_to_obj_list(path_edges)
                        for p in range(np):
                            bc.set_dst_partition_paths(d, p, obj)
                        continue

                    if P != src_prov:
                        gL = best_sel.get(P)
                        if not gL:
                            # fallback
                            obj = edges_to_obj_list(fallback_paths.get(d, []))
                            for p in range(np):
                                bc.set_dst_partition_paths(d, p, obj)
                            continue

                        k = len(gL)
                        for p in range(np):
                            g = gL[p % k]
                            part1 = src_to_g_edges.get(g)
                            if part1 is None:
                                part1 = fallback_paths.get(d, [])
                                part2 = []
                            else:
                                part2 = prov_g_tree_per_dst.get((P, g), {}).get(d)
                                if part2 is None:
                                    # fallback from gateway to dst
                                    try:
                                        part2 = _dijkstra_path_edges(G, g, d, internal_weight(P))
                                    except nx.NetworkXNoPath:
                                        part2 = []
                            full = []
                            if part1:
                                full.extend(part1)
                            if part2:
                                full.extend(part2)
                            if not full:
                                full = fallback_paths.get(d, [])
                            bc.set_dst_partition_paths(d, p, edges_to_obj_list(full))
                        continue

                    # P == src_prov but we didn't build src tree (no dsts_src or failed); fallback
                    obj = edges_to_obj_list(fallback_paths.get(d, []))
                    for p in range(np):
                        bc.set_dst_partition_paths(d, p, obj)

                return bc
            '''
        ).strip() + "\n"
        return {"code": code}

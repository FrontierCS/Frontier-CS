import json

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        algorithm_code = r'''
import networkx as nx

class BroadCastTopology:
    def __init__(self, src: str, dsts: list, num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
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


def search_algorithm(src: str, dsts: list, G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Heuristic multi-path broadcast routing:
    - For each destination, compute several near-optimal paths balancing cost and throughput.
    - Distribute partitions across up to a small number of cheapest candidate paths (to limit node/edge explosion)
      using round-robin to balance load while keeping costs low.
    """
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Candidate path configuration
    MAX_K_PATHS = max(3, min(8, num_partitions if isinstance(num_partitions, int) else 3))
    MAX_PATHS_PER_DST = max(1, min(3, num_partitions if isinstance(num_partitions, int) else 1))
    COST_TOL = 0.25  # Allow up to +25% cost over the best cost path

    # Edge weight combines egress cost with a mild penalty for low throughput
    def edge_weight(u, v, data):
        cost = data.get("cost", 0.0)
        thr = data.get("throughput", 1.0)
        if thr is None or thr <= 0:
            thr = 1e-6
        # Penalty scaled small relative to cost so cost dominates
        thr_penalty = 0.05 / thr
        return cost + thr_penalty

    def edge_cost(u, v, data):
        return data.get("cost", 0.0)

    def path_cost(path_nodes):
        total = 0.0
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            ed = G[u][v]
            total += ed.get("cost", 0.0)
        return total

    def path_min_throughput(path_nodes):
        m = float("inf")
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            thr = G[u][v].get("throughput", 0.0)
            if thr is None or thr <= 0:
                thr = 1e-6
            if thr < m:
                m = thr
        if m == float("inf"):
            m = 0.0
        return m

    def nodes_to_edge_list(path_nodes):
        edges = []
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edges.append([u, v, G[u][v]])
        return edges

    for dst in dsts:
        # Safeguard: ensure there is at least one path
        try:
            base_path = nx.dijkstra_path(G, src, dst, weight=edge_cost)
        except Exception:
            # If cost attribute missing or no path, attempt unweighted
            try:
                base_path = nx.shortest_path(G, src, dst)
            except Exception:
                # As a last resort, skip (though evaluator expects connectivity)
                continue

        base_cost = path_cost(base_path)

        # Collect candidate paths using weighted K-shortest simple paths
        candidates = []
        try:
            gen = nx.shortest_simple_paths(G, src, dst, weight=edge_weight)
            count = 0
            for pn in gen:
                candidates.append(pn)
                count += 1
                if count >= MAX_K_PATHS:
                    break
        except Exception:
            candidates = [base_path]

        # Ensure base_path is present
        present = any(tuple(p) == tuple(base_path) for p in candidates)
        if not present:
            candidates.insert(0, base_path)

        # Filter candidates by cost tolerance relative to the cheapest cost path (by pure cost)
        # First compute pure-cost-best among candidates to set a fair baseline
        pure_costs = [(path_cost(pn), idx) for idx, pn in enumerate(candidates)]
        pure_costs.sort()
        pure_best_cost = pure_costs[0][0] if pure_costs else base_cost

        filtered = []
        for pn in candidates:
            c = path_cost(pn)
            if c <= pure_best_cost * (1.0 + COST_TOL):
                filtered.append(pn)
        if not filtered:
            filtered = [base_path]

        # Rank filtered candidates: prefer lower cost, then higher min throughput, then shorter length
        filtered.sort(key=lambda pn: (path_cost(pn), -path_min_throughput(pn), len(pn)))

        # Select final paths per destination
        selected_paths = filtered[:max(1, min(MAX_PATHS_PER_DST, len(filtered)))]

        # Assign partitions round-robin across selected paths
        m = len(selected_paths)
        for pid in range(int(num_partitions)):
            chosen_path_nodes = selected_paths[pid % m]
            edges = nodes_to_edge_list(chosen_path_nodes)
            bc_topology.set_dst_partition_paths(dst, pid, edges)

    return bc_topology
'''
        return {"code": algorithm_code}
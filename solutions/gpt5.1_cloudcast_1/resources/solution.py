import json


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        num_vms = 2
        if spec_path:
            try:
                with open(spec_path, "r") as f:
                    spec = json.load(f)
                if isinstance(spec, dict):
                    v = spec.get("num_vms")
                    if isinstance(v, (int, float)) and v > 0:
                        num_vms = int(v)
            except Exception:
                pass

        algorithm_code = """
import networkx as nx

NUM_VMS = {num_vms}

EGRESS_LIMITS = {{
    "aws": 5.0,
    "gcp": 7.0,
    "azure": 16.0,
}}

THROUGHPUT_PENALTY = 0.05
EGRESS_WEIGHT = 1.0
LOAD_WEIGHT = 0.3
DEFAULT_NODE_EGRESS_LIMIT = 10.0 * NUM_VMS  # fallback if provider unknown


class BroadCastTopology:
    def __init__(self, src, dsts, num_partitions):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        self.paths = {{dst: {{str(i): None for i in range(self.num_partitions)}} for dst in dsts}}

    def append_dst_partition_path(self, dst, partition, path):
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst, partition, paths):
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions):
        self.num_partitions = num_partitions


def _get_provider(node):
    if isinstance(node, str):
        parts = node.split(":", 1)
        if len(parts) == 2:
            return parts[0]
    return None


def _build_node_egress_limits(G):
    node_limits = {{}}
    for node in G.nodes():
        prov = _get_provider(node)
        base = EGRESS_LIMITS.get(prov, DEFAULT_NODE_EGRESS_LIMIT / NUM_VMS)
        node_limits[node] = base * NUM_VMS
    return node_limits


def _prepare_graph_weights(G):
    for u, v, data in G.edges(data=True):
        thr = float(data.get("throughput", 1.0))
        if thr <= 0.0:
            thr = 1e-6
        cost = float(data.get("cost", 0.0))
        data["_sp_weight"] = cost + THROUGHPUT_PENALTY / thr


def _compute_candidate_paths(G, src, dst, max_k=4):
    paths = []
    try:
        gen = nx.shortest_simple_paths(G, src, dst, weight="_sp_weight")
        for path in gen:
            paths.append(path)
            if len(paths) >= max_k:
                break
    except Exception:
        try:
            path = nx.dijkstra_path(G, src, dst, weight="cost")
            paths = [path]
        except Exception:
            paths = []
    return paths


def search_algorithm(src, dsts, G, num_partitions):
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    if not dsts or num_partitions <= 0:
        return bc_topology

    _prepare_graph_weights(G)

    node_egr_limit = _build_node_egress_limits(G)

    max_k = max(1, min(4, num_partitions))
    candidate_paths = {{}}
    for dst in dsts:
        paths = _compute_candidate_paths(G, src, dst, max_k=max_k)
        if not paths:
            try:
                paths = [nx.dijkstra_path(G, src, dst, weight="cost")]
            except Exception:
                paths = []
        candidate_paths[dst] = paths

    for dst in dsts:
        if not candidate_paths.get(dst):
            return bc_topology

    edge_partition_counts = {{}}
    node_out_partitions = {{}}
    global_max_edge_load = 0.0
    global_max_node_load = 0.0

    def _edge_thr(u, v):
        data = G[u][v]
        thr = float(data.get("throughput", 1.0))
        if thr <= 0.0:
            return 1e-6
        return thr

    for part in range(num_partitions):
        for dst in dsts:
            paths = candidate_paths[dst]
            if not paths:
                continue

            best_score = None
            best_path = None
            best_egress = None

            for path in paths:
                if len(path) < 2:
                    continue
                path_edges = list(zip(path[:-1], path[1:]))

                egress_inc = 0.0
                for u, v in path_edges:
                    egress_inc += float(G[u][v].get("cost", 0.0))

                path_max_load = global_max_edge_load if global_max_edge_load > global_max_node_load else global_max_node_load

                for u, v in path_edges:
                    key = (u, v)
                    curr_count = edge_partition_counts.get(key, 0)
                    new_count = curr_count + 1
                    thr = _edge_thr(u, v)
                    new_load = new_count / thr
                    if new_load > path_max_load:
                        path_max_load = new_load

                for u in path[:-1]:
                    base_out = node_out_partitions.get(u, 0)
                    new_out = base_out + 1
                    lim = float(node_egr_limit.get(u, DEFAULT_NODE_EGRESS_LIMIT))
                    if lim <= 0.0:
                        lim = 1e-6
                    new_node_load = new_out / lim
                    if new_node_load > path_max_load:
                        path_max_load = new_node_load

                score = EGRESS_WEIGHT * egress_inc + LOAD_WEIGHT * path_max_load

                if best_score is None or score < best_score:
                    best_score = score
                    best_path = path
                    best_egress = egress_inc
                elif score == best_score:
                    if best_egress is None or egress_inc < best_egress:
                        best_score = score
                        best_path = path
                        best_egress = egress_inc
                    elif egress_inc == best_egress and len(path) < len(best_path):
                        best_score = score
                        best_path = path
                        best_egress = egress_inc

            if best_path is None:
                continue

            chosen_edges = list(zip(best_path[:-1], best_path[1:]))

            for u, v in chosen_edges:
                key = (u, v)
                new_count = edge_partition_counts.get(key, 0) + 1
                edge_partition_counts[key] = new_count
                thr = _edge_thr(u, v)
                new_edge_load = new_count / thr
                if new_edge_load > global_max_edge_load:
                    global_max_edge_load = new_edge_load

            for u in best_path[:-1]:
                new_out = node_out_partitions.get(u, 0) + 1
                node_out_partitions[u] = new_out
                lim = float(node_egr_limit.get(u, DEFAULT_NODE_EGRESS_LIMIT))
                if lim <= 0.0:
                    lim = 1e-6
                new_node_load = new_out / lim
                if new_node_load > global_max_node_load:
                    global_max_node_load = new_node_load

            edge_list = []
            for u, v in chosen_edges:
                edge_list.append([u, v, G[u][v]])

            bc_topology.set_dst_partition_paths(dst, part, edge_list)

    return bc_topology
""".format(num_vms=num_vms)

        return {"code": algorithm_code}

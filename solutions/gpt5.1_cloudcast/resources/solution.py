import json


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        try:
            if spec_path is not None:
                with open(spec_path, "r") as f:
                    _ = json.load(f)
        except Exception:
            pass

        algorithm_code = '''import networkx as nx
from collections import defaultdict


class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {dst: {partition_id: [edges]}}
        # Each edge is [src_node, dst_node, edge_data_dict]
        self.paths = {
            dst: {str(i): None for i in range(self.num_partitions)}
            for dst in dsts
        }

    def append_dst_partition_path(self, dst: str, partition: int, path: list):
        """
        Append an edge to the path for a specific destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID (0 to num_partitions-1)
            path: Edge represented as [src_node, dst_node, edge_data_dict]
                  where edge_data_dict = G[src_node][dst_node]
        """
        partition = str(partition)
        if self.paths[dst][partition] is None:
            self.paths[dst][partition] = []
        self.paths[dst][partition].append(path)

    def set_dst_partition_paths(self, dst: str, partition: int, paths: list[list]):
        """
        Set the complete path (list of edges) for a destination-partition pair.

        Args:
            dst: Destination node
            partition: Partition ID
            paths: List of edges, each edge is [src_node, dst_node, edge_data_dict]
        """
        partition = str(partition)
        self.paths[dst][partition] = paths

    def set_num_partitions(self, num_partitions: int):
        """Update number of partitions"""
        self.num_partitions = num_partitions


def _compute_beta(G: nx.DiGraph) -> float:
    """
    Compute a scaling factor beta to balance egress cost and load/throughput
    in the edge weight function.
    """
    total_cost = 0.0
    total_thr = 0.0
    count_cost = 0
    count_thr = 0

    for _, _, data in G.edges(data=True):
        c = data.get("cost", 0.0)
        t = data.get("throughput", 0.0)
        if c > 0.0:
            total_cost += c
            count_cost += 1
        if t > 0.0:
            total_thr += t
            count_thr += 1

    if count_cost == 0:
        avg_cost = 0.01
    else:
        avg_cost = total_cost / count_cost

    if count_thr == 0:
        avg_thr = 1.0
    else:
        avg_thr = total_thr / count_thr

    beta = avg_cost * avg_thr
    if beta <= 0.0:
        beta = 0.01
    return beta


def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    """
    Design routing paths for broadcasting data partitions to multiple destinations.

    Heuristic:
    - For each (destination, partition) pair, run a Dijkstra search with a
      dynamic edge weight that depends on:
        * monetary cost ("cost" attribute)
        * current logical load on the edge (how many partitions already use it)
        * edge throughput ("throughput" attribute)
    - This encourages low-cost, high-throughput, and less loaded paths, which
      approximately balances egress and transfer-time costs.
    """
    num_partitions = int(num_partitions)
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    # Logical load: number of partitions currently assigned to each directed edge.
    edge_load = defaultdict(int)

    beta = _compute_beta(G)

    def weight(u, v, data):
        cost = data.get("cost", 0.0)
        thr = data.get("throughput", 0.0)
        if thr <= 0.0:
            thr = 1e-6  # effectively unusable edge
        load = edge_load[(u, v)]
        # Approximate time impact: (current_load + 1) / throughput
        time_penalty = (load + 1.0) / thr
        return cost + beta * time_penalty

    # Assign partitions in round-robin over destinations to spread initial load.
    for p in range(num_partitions):
        for dst in dsts:
            if src == dst:
                # Trivial case: no transfer needed.
                bc_topology.set_dst_partition_paths(dst, p, [])
                continue

            try:
                path_nodes = nx.dijkstra_path(G, src, dst, weight=weight)
            except nx.NetworkXNoPath:
                # Fallback: try unweighted shortest path; if this also fails,
                # let the exception propagate as there is no valid topology.
                path_nodes = nx.shortest_path(G, src, dst)

            # Convert node path to edge list and update loads.
            edges_list = []
            for i in range(len(path_nodes) - 1):
                u = path_nodes[i]
                v = path_nodes[i + 1]
                edge_data = G[u][v]
                edges_list.append([u, v, edge_data])
                edge_load[(u, v)] += 1

            bc_topology.set_dst_partition_paths(dst, p, edges_list)

    return bc_topology
'''
        return {"code": algorithm_code}

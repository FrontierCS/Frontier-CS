import json
import textwrap


class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with a python_code_string for the search algorithm.
        """
        num_vms = 2
        if spec_path:
            try:
                with open(spec_path, 'r') as f:
                    spec = json.load(f)
                    num_vms = spec.get('num_vms', 2)
            except (IOError, json.JSONDecodeError):
                # If spec_path is invalid or not found, use the default value.
                pass

        algorithm_code = f"""
import networkx as nx
from collections import defaultdict
import random
from itertools import islice
import math

class BroadCastTopology:
    def __init__(self, src: str, dsts: list[str], num_partitions: int):
        self.src = src
        self.dsts = dsts
        self.num_partitions = int(num_partitions)
        # Structure: {{dst: {{partition_id: [edges]}}}}
        # Each edge is [src_node, dst_node, edge_data_dict]
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

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> BroadCastTopology:
    
    random.seed(42)
    
    # Constants from the problem description, with num_vms injected from spec.
    NUM_VMS = {num_vms}
    INSTANCE_RATE = 0.54  # $/hour
    INGRESS_LIMITS = {{"aws": 10, "gcp": 16, "azure": 16}}  # Gbps
    EGRESS_LIMITS = {{"aws": 5, "gcp": 7, "azure": 16}}  # Gbps

    # --- Helper Functions (defined inside for encapsulation) ---

    def get_provider(node):
        return node.split(':')[0]

    def path_to_edges(path, graph):
        return [[path[i], path[i + 1], graph[path[i]][path[i + 1]]] for i in range(len(path) - 1)]

    def calculate_total_cost(topology: BroadCastTopology, graph: nx.DiGraph):
        s_partition = 1.0

        edge_partitions = defaultdict(list)
        used_nodes = set()
        node_outgoing_edges = defaultdict(set)
        node_incoming_edges = defaultdict(set)
        used_edges = set()

        for dst in topology.dsts:
            for i in range(topology.num_partitions):
                path = topology.paths[dst][str(i)]
                if not path: return float('inf'), None, None
                if path[0][0] != src or path[-1][1] != dst: return float('inf'), None, None
                for u, v, _ in path:
                    edge = (u, v)
                    edge_partitions[edge].append((dst, i))
                    used_edges.add(edge)
        
        if not used_edges: return 0.0, None, defaultdict(list)

        for u, v in used_edges:
            used_nodes.add(u); used_nodes.add(v)
            node_outgoing_edges[u].add((u, v))
            node_incoming_edges[v].add((u, v))

        c_egress = sum(
            len(partitions) * s_partition * graph[u][v]['cost']
            for (u, v), partitions in edge_partitions.items()
        )

        actual_throughputs = {{}}
        for u, v in used_edges:
            provider_u, provider_v = get_provider(u), get_provider(v)
            egress_limit_u = EGRESS_LIMITS.get(provider_u, float('inf')) * NUM_VMS
            ingress_limit_v = INGRESS_LIMITS.get(provider_v, float('inf')) * NUM_VMS
            
            num_out = len(node_outgoing_edges[u])
            num_in = len(node_incoming_edges[v])

            shared_egress_u = egress_limit_u / num_out if num_out > 0 else float('inf')
            shared_ingress_v = ingress_limit_v / num_in if num_in > 0 else float('inf')
            
            f_e = min(graph[u][v]['throughput'], shared_egress_u, shared_ingress_v)
            actual_throughputs[(u, v)] = f_e

        max_t, bottleneck_edge = 0.0, None
        for edge, partitions in edge_partitions.items():
            f_e = actual_throughputs[edge]
            if f_e <= 1e-9: return float('inf'), edge, edge_partitions
            t_edge = (len(partitions) * s_partition * 8) / f_e
            if t_edge > max_t:
                max_t, bottleneck_edge = t_edge, edge
        
        t_transfer = max_t
        c_instance = len(used_nodes) * NUM_VMS * (INSTANCE_RATE / 3600) * t_transfer

        return c_egress + c_instance, bottleneck_edge, edge_partitions

    # --- Main Algorithm Logic ---

    # 1. Initial Solution: Find K cheapest paths for each destination and
    #    distribute partitions among them using round-robin to balance load.
    K_PATHS = 5
    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    dst_candidate_paths = {{}}

    for dst in dsts:
        try:
            paths_gen = nx.shortest_simple_paths(G, src, dst, weight='cost')
            dst_candidate_paths[dst] = [path_to_edges(p, G) for p in islice(paths_gen, K_PATHS)]
        except nx.NetworkXNoPath:
            dst_candidate_paths[dst] = []

        if not dst_candidate_paths[dst]:
            # This destination is unreachable, we cannot create a valid topology.
            return bc_topology

    for dst, paths in dst_candidate_paths.items():
        if not paths: continue
        for i in range(num_partitions):
            path_to_use = paths[i % len(paths)]
            bc_topology.set_dst_partition_paths(dst, i, path_to_use)

    # 2. Iterative Improvement: Use a greedy local search to refine the topology.
    #    It identifies the main bottleneck and tries to reroute one partition away from it.
    best_topology = bc_topology
    cost, bottleneck, edge_map = calculate_total_cost(best_topology, G)
    if not math.isfinite(cost):
        return best_topology

    best_cost = cost
    
    max_iterations = min(500, 20 * num_partitions)

    for _ in range(max_iterations):
        if bottleneck is None: break

        partitions_on_bottleneck = edge_map.get(bottleneck)
        if not partitions_on_bottleneck: break
            
        dst_victim, p_victim = random.choice(partitions_on_bottleneck)
        
        G_temp = G.copy()
        u, v = bottleneck
        # Penalize the bottleneck edge to encourage finding an alternative path
        G_temp.add_edge(u, v, cost=G[u][v]['cost'] * 10, throughput=G[u][v]['throughput'])
        
        try:
            new_path_nodes = nx.dijkstra_path(G_temp, src, dst_victim, weight='cost')
            new_path_edges = path_to_edges(new_path_nodes, G)
        except nx.NetworkXNoPath:
            # No alternative path found, try rerouting another partition
            continue

        # Evaluate the move by calculating cost of the new topology
        temp_topology = BroadCastTopology(src, dsts, num_partitions)
        temp_topology.paths = {{d: p.copy() for d, p in best_topology.paths.items()}}
        temp_topology.set_dst_partition_paths(dst_victim, p_victim, new_path_edges)
        
        new_cost, new_bottleneck, new_edge_map = calculate_total_cost(temp_topology, G)

        # Greedy update: if the new topology is better, accept it
        if new_cost < best_cost:
            best_cost, best_topology = new_cost, temp_topology
            bottleneck, edge_map = new_bottleneck, new_edge_map

    return best_topology
"""
        return {"code": textwrap.dedent(algorithm_code).strip()}

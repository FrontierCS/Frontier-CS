import json

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dict with either:
        - {"code": "python_code_string"}
        - {"program_path": "path/to/algorithm.py"}
        """
        num_vms = 2  # Default value
        if spec_path:
            try:
                with open(spec_path, 'r') as f:
                    spec_data = json.load(f)
                num_vms = spec_data.get("num_vms", 2)
            except (FileNotFoundError, json.JSONDecodeError):
                # If the file is not found or is invalid, use the default value.
                pass

        # The algorithm code is generated as a string.
        # This allows embedding constants like num_vms read from the spec file.
        python_code_string = f"""
import networkx as nx
import itertools
from collections import defaultdict

# The BroadCastTopology class is provided in the evaluation environment.
# It is defined here so that this code string is a self-contained,
# runnable script for development and testing purposes.
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
    \"\"\"
    Designs routing paths for broadcasting data partitions to multiple destinations.
    This algorithm aims to minimize total cost by balancing egress cost and instance cost.
    It does this by finding K paths for each destination that are good in terms of both
    low cost and high throughput. Partitions are then distributed among these paths
    in a round-robin fashion to balance the load and minimize transfer time.
    \"\"\"

    # --- Constants and Parameters ---
    NUM_VMS = {num_vms}
    INSTANCE_HOURLY_RATE = 0.54  # $/hour, from problem spec

    # Heuristic parameter: Number of alternative paths for load balancing
    K_PATHS = 3

    # --- Composite Edge Weight Calculation ---
    # The core of the heuristic is a composite edge weight that balances the two
    # components of the total cost: egress cost and instance cost (related to time).
    # weight(e) = egress_cost_per_gb(e) + C_balance * time_cost_proxy(e)
    # egress_cost_per_gb(e) = G.edges[e]['cost']
    # time_cost_proxy(e) = 1 / G.edges[e]['throughput']
    # C_balance is a constant to make the units compatible ($/GB vs $/Gbps).

    # Estimate the number of nodes that will be part of the final topology.
    # Using the total number of nodes in the graph is a safe (though loose) upper bound.
    num_nodes_estimate = len(G.nodes)
    if num_nodes_estimate == 0:
        # Handle empty graph case
        return BroadCastTopology(src, dsts, num_partitions)

    # Calculate C_balance:
    # C_instance_per_sec = |V| * n_vm * r_instance / 3600
    # Time to transfer 1 GB = 8 Gbit / throughput_gbps = 8 / throughput
    # Instance cost to transfer 1 GB = C_instance_per_sec * (8 / throughput)
    # So, the balancing factor for (1/throughput) is C_instance_per_sec * 8.
    c_instance_per_sec = num_nodes_estimate * NUM_VMS * INSTANCE_HOURLY_RATE / 3600
    C_BALANCE = c_instance_per_sec * 8

    for u, v, data in G.edges(data=True):
        cost = data.get('cost', float('inf'))
        throughput = data.get('throughput', 0)
        
        if throughput > 1e-9: # Use a small epsilon for floating point comparison
            time_penalty = C_BALANCE / throughput
            G.edges[u, v]['composite_weight'] = cost + time_penalty
        else:
            # Assign a very high weight to edges with zero or negligible throughput
            G.edges[u, v]['composite_weight'] = float('inf')

    # --- Path Finding and Partition Assignment ---
    bc_topology = BroadCastTopology(src, dsts, num_partitions)

    for dst in dsts:
        k_shortest_paths = []
        try:
            # Find K shortest simple paths from source to destination
            # using the calculated composite weight.
            paths_generator = nx.shortest_simple_paths(G, src, dst, weight='composite_weight')
            k_shortest_paths = list(itertools.islice(paths_generator, K_PATHS))
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            # Fallback if no path is found with the composite weight.
            # This can happen if all paths have infinite weight.
            pass

        if not k_shortest_paths:
            # If the primary strategy fails, fall back to finding a single
            # shortest path based purely on egress cost.
            try:
                path = nx.dijkstra_path(G, src, dst, weight='cost')
                k_shortest_paths = [path]
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                # This case implies the destination is unreachable, which contradicts
                # the problem's implicit assumption of a connected graph.
                continue
        
        # Distribute partitions across the found paths using a round-robin strategy.
        # This balances the load (|P_e|) across multiple network routes.
        num_found_paths = len(k_shortest_paths)
        if num_found_paths == 0:
            continue
            
        for partition_id in range(num_partitions):
            # Select a path for the current partition
            path_nodes = k_shortest_paths[partition_id % num_found_paths]
            
            # Convert the list of nodes into the required list of edges format
            edge_path = []
            for i in range(len(path_nodes) - 1):
                u, v = path_nodes[i], path_nodes[i+1]
                edge_path.append([u, v, G.edges[u, v]])
            
            bc_topology.set_dst_partition_paths(dst, partition_id, edge_path)

    return bc_topology
"""
        return {"code": python_code_string}

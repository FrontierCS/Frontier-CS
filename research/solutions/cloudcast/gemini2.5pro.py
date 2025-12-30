import json
import textwrap

class Solution:
    def solve(self, spec_path: str = None) -> dict:
        """
        Returns a dictionary containing the Python code for the search algorithm.

        The method reads the number of VMs from the spec file and injects it
        into the algorithm code string. This makes the algorithm aware of the
        specifics of the evaluation environment.
        """
        num_vms = 2  # Default value
        if spec_path:
            try:
                with open(spec_path, 'r') as f:
                    spec_data = json.load(f)
                num_vms = spec_data.get("num_vms", 2)
            except (FileNotFoundError, json.JSONDecodeError):
                # Fallback to default if spec file is invalid or not found
                pass

        # The algorithm's Python code is generated as a string.
        # This allows for dynamic configuration based on the spec file.
        python_code_string = f"""
import networkx as nx
from collections import defaultdict

# The BroadCastTopology class is provided by the evaluation environment and
# is expected to be in the global scope when this function is executed.

def search_algorithm(src: str, dsts: list[str], G: nx.DiGraph, num_partitions: int) -> 'BroadCastTopology':
    \"\"\"
    Designs routing paths by sequentially finding congestion-aware shortest paths.

    This algorithm addresses the trade-off between minimizing egress cost and instance
    cost. Instance cost is primarily driven by transfer time, which in turn depends
    on network congestion. To tackle this, the algorithm iteratively routes each
    data partition, making each routing decision aware of the network load from
    previously routed partitions.

    The core of the algorithm is a dynamic edge weight function used with Dijkstra's
    shortest path algorithm. This weight function is a composite of three factors:
    1.  Base Egress Cost: The standard $/GB cost for using an edge.
    2.  Latency Proxy: A term inversely proportional to the edge's maximum
        throughput. This penalizes slower links that are likely to increase the
        overall transfer time and, consequently, the instance cost.
    3.  Congestion Penalty: A multiplicative factor that increases with the number
        of partitions already routed over an edge. This key component encourages
        load balancing by making congested paths more "expensive" for subsequent
        partitions, steering them towards underutilized routes.

    By iterating through partitions and sequentially building up the broadcast
    topology, the algorithm adapts to its own routing decisions, effectively
    spreading the data load across the network to avoid bottlenecks.
    \"\"\"

    # --- Constants and Tuning Parameters ---

    # Number of VMs per region, obtained from the evaluation spec file.
    NUM_VMS = {num_vms}
    
    # A weighting factor to balance the importance of egress cost versus instance
    # cost (approximated by latency). This value is derived from an analysis
    # of the problem's cost function and can be tuned. A higher value prioritizes
    # finding paths with higher throughput.
    INSTANCE_COST_WEIGHT = 0.15

    # A factor that controls how aggressively the algorithm avoids congestion.
    # A higher value results in a stronger penalty for using an already-loaded
    # edge, leading to more diverse paths for different partitions.
    CONGESTION_PENALTY_FACTOR = 0.5

    # --- Algorithm Implementation ---

    bc_topology = BroadCastTopology(src, dsts, num_partitions)
    
    # A dictionary to track the usage of each edge, i.e., how many partitions
    # are routed through it. Key: (u, v) tuple, Value: integer count.
    edge_usage = defaultdict(int)

    # Pre-calculate a 'base_weight' for each edge to optimize the main loop.
    # This base weight combines the static egress cost and the latency proxy.
    for u, v, data in G.edges(data=True):
        cost = data.get('cost', 0.0)
        throughput = data.get('throughput', 1e-9)
        if throughput <= 0:
            throughput = 1e-9
        
        data['base_weight'] = cost + INSTANCE_COST_WEIGHT / throughput

    # The main loop iterates through each partition and finds a path to every
    # destination. This sequential approach is crucial for load balancing.
    for partition_id in range(num_partitions):
        for dst in dsts:
            
            # This callable is passed to networkx's Dijkstra implementation.
            # It calculates the edge weight on-the-fly, incorporating the
            # current congestion.
            def dynamic_weight_func(u, v, edge_data):
                edge = (u, v)
                usage = edge_usage.get(edge, 0)
                
                # The penalty grows linearly with the number of partitions on the edge.
                congestion_penalty = 1.0 + CONGESTION_PENALTY_FACTOR * usage
                return edge_data['base_weight'] * congestion_penalty

            # Find the optimal path for the current partition and destination
            # using the congestion-aware weights.
            path_nodes = nx.dijkstra_path(G, src, dst, weight=dynamic_weight_func)
            
            # Convert the node-based path to an edge-based path and update
            # the topology and usage counts.
            path_edges = []
            for i in range(len(path_nodes) - 1):
                u, v = path_nodes[i], path_nodes[i+1]
                edge = (u, v)
                
                edge_usage[edge] += 1
                path_edges.append([u, v, G[u][v]])

            bc_topology.set_dst_partition_paths(dst, partition_id, path_edges)
            
    return bc_topology
"""
        return {"code": textwrap.dedent(python_code_string).strip()}
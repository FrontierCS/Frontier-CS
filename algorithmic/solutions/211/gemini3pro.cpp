#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <iomanip>

using namespace std;

// Define structure for nodes representing robots and relay stations
struct Node {
    int id;
    long long x, y;
    char type; // 'R' for Ordinary Robot, 'S' for High-Power Robot, 'C' for Relay Station
};

// Global variables
int N, K;
vector<Node> nodes;

// Function to calculate squared Euclidean distance between two nodes
double get_dist_sq(const Node& a, const Node& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    return (double)(dx * dx + dy * dy);
}

// Function to calculate communication energy consumption cost (edge weight)
double get_weight(const Node& a, const Node& b) {
    // Relay stations cannot communicate directly with each other
    if (a.type == 'C' && b.type == 'C') return 1e18; // Infinity
    
    double d2 = get_dist_sq(a, b);
    
    // Relay station involved (C-R or C-S) -> Cost is 1.0 * D
    if (a.type == 'C' || b.type == 'C') return d2;
    
    // Both are Ordinary Robots (R-R) -> Cost is 1.0 * D
    if (a.type == 'R' && b.type == 'R') return d2;
    
    // At least one High-Power Robot involved (R-S, S-R, S-S) -> Cost is 0.8 * D
    return 0.8 * d2;
}

// Structure to represent an edge in the MST
struct Edge {
    int u, v; // Indices in the global 'nodes' vector
    double w;
};

// Function to compute the Minimum Spanning Tree (MST) for a subset of nodes using Prim's algorithm
// Returns the total cost and the list of edges in the MST
pair<double, vector<Edge>> compute_mst(const vector<int>& active_indices) {
    int n = active_indices.size();
    if (n == 0) return {0.0, {}};
    
    // min_w[i] stores the minimum weight to connect node i (local index) to the MST
    vector<double> min_w(n, 1e18);
    // parent[i] stores the parent of node i (local index) in the MST
    vector<int> parent(n, -1);
    // in_mst[i] is true if node i is already included in the MST
    vector<bool> in_mst(n, false);
    
    // Start from the first node in the subset
    min_w[0] = 0;
    double total_cost = 0;
    vector<Edge> result_edges;
    
    for (int i = 0; i < n; ++i) {
        int u = -1;
        // Find the node with the smallest min_w not yet in MST
        for (int j = 0; j < n; ++j) {
            if (!in_mst[j] && (u == -1 || min_w[j] < min_w[u])) {
                u = j;
            }
        }
        
        // If the remaining nodes are unreachable (disconnected), stop
        if (min_w[u] == 1e18) break;
        
        in_mst[u] = true;
        total_cost += min_w[u];
        
        // If not the root, add the edge to the results
        if (parent[u] != -1) {
            result_edges.push_back({active_indices[u], active_indices[parent[u]], min_w[u]});
        }
        
        // Update weights for neighbors of u
        int u_global = active_indices[u];
        for (int v = 0; v < n; ++v) {
            if (!in_mst[v]) {
                int v_global = active_indices[v];
                double w = get_weight(nodes[u_global], nodes[v_global]);
                if (w < min_w[v]) {
                    min_w[v] = w;
                    parent[v] = u;
                }
            }
        }
    }
    
    return {total_cost, result_edges};
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;

    nodes.resize(N + K);
    vector<int> current_indices;
    // Reading input
    for (int i = 0; i < N + K; ++i) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
        current_indices.push_back(i);
    }

    // Iterative algorithm to select the best subset of relay stations
    // Strategy: Start with all nodes, then iteratively remove useless relay stations.
    while (true) {
        // 1. Compute MST on the current set of nodes
        pair<double, vector<Edge>> res = compute_mst(current_indices);
        vector<Edge>& mst_edges = res.second;
        
        // 2. Build adjacency list for the current MST to analyze node degrees
        vector<vector<int>> adj(N + K);
        for (const auto& e : mst_edges) {
            adj[e.u].push_back(e.v);
            adj[e.v].push_back(e.u);
        }
        
        vector<int> to_remove;
        
        // 3. Identify inefficient Relay Stations
        for (int idx : current_indices) {
            if (nodes[idx].type == 'C') {
                const auto& neighbors = adj[idx];
                
                // If a relay station is a leaf (degree 1) or isolated, it is not helping connectivity efficiently.
                // Removing it reduces total cost.
                if (neighbors.size() <= 1) {
                    to_remove.push_back(idx);
                    continue;
                }
                
                // If a relay station has degree >= 2, check if it actually saves energy compared to
                // connecting its neighbors directly (or via other paths).
                
                // Calculate current cost contribution of this relay (sum of edges to neighbors)
                double current_local_cost = 0;
                for (int nbr : neighbors) {
                    current_local_cost += get_weight(nodes[idx], nodes[nbr]);
                }
                
                // Calculate the cost to connect these neighbors without the relay.
                // We compute the MST of the neighbor set.
                // Note: Neighbors of a 'C' node are always 'R' or 'S' (since C-C is forbidden).
                pair<double, vector<Edge>> alt_res = compute_mst(neighbors);
                double alt_cost = alt_res.first;
                
                // If the relay station's local edges are more expensive than (or equal to) the alternative,
                // it is inefficient and should be removed. Tolerance 1e-9 for float comparison.
                if (current_local_cost >= alt_cost - 1e-9) {
                    to_remove.push_back(idx);
                }
            }
        }
        
        // If no relay stations were marked for removal, the set is stable/optimal.
        if (to_remove.empty()) break;
        
        // Remove marked nodes from the active set
        vector<bool> removing(N + K, false);
        for (int r : to_remove) removing[r] = true;
        
        vector<int> next_indices;
        next_indices.reserve(current_indices.size() - to_remove.size());
        for (int idx : current_indices) {
            if (!removing[idx]) {
                next_indices.push_back(idx);
            }
        }
        current_indices = next_indices;
    }

    // Compute final MST for the optimized set of nodes
    pair<double, vector<Edge>> final_res = compute_mst(current_indices);
    const vector<Edge>& edges = final_res.second;

    // Output 1: IDs of selected relay stations
    vector<int> relay_ids;
    for (int idx : current_indices) {
        if (nodes[idx].type == 'C') {
            relay_ids.push_back(nodes[idx].id);
        }
    }
    sort(relay_ids.begin(), relay_ids.end());
    
    if (relay_ids.empty()) {
        cout << "#" << endl;
    } else {
        for (size_t i = 0; i < relay_ids.size(); ++i) {
            cout << relay_ids[i] << (i == relay_ids.size() - 1 ? "" : "#");
        }
        cout << endl;
    }
    
    // Output 2: Communication links
    for (size_t i = 0; i < edges.size(); ++i) {
        int u = edges[i].u;
        int v = edges[i].v;
        int id1 = nodes[u].id;
        int id2 = nodes[v].id;
        cout << id1 << "-" << id2 << (i == edges.size() - 1 ? "" : "#");
    }
    cout << endl;

    return 0;
}
#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <string>
#include <set>

using namespace std;

// Structure to represent a device
struct Node {
    int id;
    long long x, y;
    char type; // 'R', 'S', 'C'
    int original_index;
};

int N, K;
vector<Node> all_nodes;
vector<int> req_indices; // Indices of R and S nodes
vector<int> opt_indices; // Indices of C nodes

// Helper to compute squared Euclidean distance
double get_dist_sq(const Node& a, const Node& b) {
    return (double)((a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y));
}

// Compute weight between two nodes based on their types
double get_weight(int i, int j) {
    const Node& u = all_nodes[i];
    const Node& v = all_nodes[j];
    
    // Relay stations cannot communicate directly
    if (u.type == 'C' && v.type == 'C') return 1e18; 
    
    double dist = get_dist_sq(u, v);
    
    // Connection involving a Relay Station
    if (u.type == 'C' || v.type == 'C') {
        return dist; // 1.0 * D
    }
    
    // Connection between R/S nodes
    if (u.type == 'S' || v.type == 'S') {
        return 0.8 * dist; // One or both are S
    }
    
    // Both are R
    return dist; // 1.0 * D
}

// Standard Prim's Algorithm to find MST of a subset of nodes
// Returns {total_cost, list_of_edges}
// edges are pairs of indices in 'all_nodes'
pair<double, vector<pair<int, int>>> run_prim(const vector<int>& nodes_subset) {
    int n = nodes_subset.size();
    if (n == 0) return {0.0, {}};

    vector<double> min_w(n, 1e18);
    vector<int> parent(n, -1);
    vector<bool> in_mst(n, false);
    
    min_w[0] = 0;
    double total_cost = 0;
    
    for (int i = 0; i < n; ++i) {
        int u = -1;
        double best = 1e18;
        for (int j = 0; j < n; ++j) {
            if (!in_mst[j] && min_w[j] < best) {
                best = min_w[j];
                u = j;
            }
        }
        
        if (u == -1) break; 
        
        in_mst[u] = true;
        total_cost += best;
        
        int global_u = nodes_subset[u];
        
        for (int v = 0; v < n; ++v) {
            if (!in_mst[v]) {
                int global_v = nodes_subset[v];
                double w = get_weight(global_u, global_v);
                if (w < min_w[v]) {
                    min_w[v] = w;
                    parent[v] = u;
                }
            }
        }
    }
    
    vector<pair<int, int>> edges;
    for (int i = 1; i < n; ++i) {
        if (parent[i] != -1) {
            edges.push_back({nodes_subset[i], nodes_subset[parent[i]]});
        }
    }
    
    return {total_cost, edges};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;

    all_nodes.resize(N + K);
    for (int i = 0; i < N + K; ++i) {
        cin >> all_nodes[i].id >> all_nodes[i].x >> all_nodes[i].y >> all_nodes[i].type;
        all_nodes[i].original_index = i;
        if (all_nodes[i].type == 'C') {
            opt_indices.push_back(i);
        } else {
            req_indices.push_back(i);
        }
    }

    // 1. Calculate Base MST (using only R and S nodes)
    pair<double, vector<pair<int, int>>> base_res = run_prim(req_indices);
    double base_cost = base_res.first;

    // 2. Try to improve using Relay Stations
    // Heuristic: Start with all C nodes, then iteratively prune "useless" ones.
    vector<int> active_C = opt_indices;
    double best_aug_cost = 1e18;
    vector<pair<int, int>> best_aug_edges;
    vector<int> final_C_indices;
    
    bool changed = true;
    while (changed) {
        changed = false;
        
        vector<int> nodes = req_indices;
        nodes.insert(nodes.end(), active_C.begin(), active_C.end());
        
        // Compute MST with current active relays
        pair<double, vector<pair<int, int>>> res = run_prim(nodes);
        double cur_cost = res.first;
        vector<pair<int, int>> edges = res.second;
        
        // Build adjacency list for topological analysis
        vector<vector<int>> adj(N + K); 
        for (auto& e : edges) {
            adj[e.first].push_back(e.second);
            adj[e.second].push_back(e.first);
        }
        
        set<int> to_remove;
        
        // Compute degrees
        vector<int> deg(N + K, 0);
        for(int u : nodes) deg[u] = adj[u].size();
        
        // Step 2a: Recursively prune degree-1 Relay nodes (leaves)
        vector<int> q;
        for (int c : active_C) {
            if (deg[c] <= 1) q.push_back(c);
        }
        
        int head = 0;
        while(head < q.size()){
            int u = q[head++];
            to_remove.insert(u);
            for(int v : adj[u]){
                if (to_remove.count(v)) continue; 
                deg[v]--;
                if (deg[v] == 1 && all_nodes[v].type == 'C') {
                    q.push_back(v);
                }
            }
        }

        // Step 2b: Check if remaining Relays are locally optimal
        // Compare "Star" cost (relay to neighbors) vs "Clique" cost (neighbors directly connected)
        for (int c : active_C) {
            if (to_remove.count(c)) continue;
            
            vector<int> neighbors;
            for(int v : adj[c]) {
                if (!to_remove.count(v)) neighbors.push_back(v);
            }
            
            // If degree became < 2 after pruning neighbors, it should be removed (logic above handles it mostly, but double check)
            if (neighbors.size() < 2) {
                to_remove.insert(c);
                continue;
            }
            
            double star_cost = 0;
            for(int v : neighbors) star_cost += get_weight(c, v);
            
            // Compute MST of the neighbors connected directly
            pair<double, vector<pair<int,int>>> clique_res = run_prim(neighbors);
            double clique_cost = clique_res.first;
            
            // If direct connection is cheaper, the relay is not helpful
            if (star_cost > clique_cost + 1e-9) { 
                to_remove.insert(c);
            }
        }
        
        // Update active set
        if (!to_remove.empty()) {
            vector<int> next_active;
            for(int c : active_C) {
                if (!to_remove.count(c)) next_active.push_back(c);
            }
            if (next_active.size() != active_C.size()) {
                active_C = next_active;
                changed = true;
            }
        } else {
            // No changes, store this solution
            best_aug_cost = cur_cost;
            best_aug_edges = edges;
            final_C_indices = active_C;
        }
    }
    
    // 3. Output best solution
    vector<pair<int,int>> output_edges;
    vector<int> output_c;
    bool use_base = (base_cost <= best_aug_cost);

    if (use_base) {
        for(auto& e : base_res.second) output_edges.push_back({all_nodes[e.first].id, all_nodes[e.second].id});
    } else {
        for(int idx : final_C_indices) output_c.push_back(all_nodes[idx].id);
        for(auto& e : best_aug_edges) output_edges.push_back({all_nodes[e.first].id, all_nodes[e.second].id});
    }

    // Format Output
    sort(output_c.begin(), output_c.end());
    if (output_c.empty()) cout << "#" << endl;
    else {
        for(size_t i=0; i<output_c.size(); ++i) {
            cout << output_c[i] << (i==output_c.size()-1 ? "" : "#");
        }
        cout << endl;
    }

    // Ensure edge links are ordered smaller-ID first
    for(auto& p : output_edges) {
        if(p.first > p.second) swap(p.first, p.second);
    }
    sort(output_edges.begin(), output_edges.end());

    for(size_t i=0; i<output_edges.size(); ++i) {
        cout << output_edges[i].first << "-" << output_edges[i].second << (i==output_edges.size()-1 ? "" : "#");
    }
    cout << endl;

    return 0;
}
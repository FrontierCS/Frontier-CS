#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <set>

using namespace std;

// Data structure for devices
struct Point {
    int id;
    int x, y;
    char type; // 'R', 'S', 'C'
};

int N, K;
vector<Point> devices;

// Squared Euclidean distance
long long distSq(int i, int j) {
    long long dx = devices[i].x - devices[j].x;
    long long dy = devices[i].y - devices[j].y;
    return dx*dx + dy*dy;
}

// Cost calculation based on rules
double get_cost(int i, int j) {
    long long d2 = distSq(i, j);
    char t1 = devices[i].type;
    char t2 = devices[j].type;

    if (t1 == 'C' || t2 == 'C') {
        // Relay to any robot cost is 1 * D
        return (double)d2;
    }
    
    // S to S or S to R cost is 0.8 * D
    if (t1 == 'S' || t2 == 'S') {
        return 0.8 * d2;
    }
    
    // R to R cost is 1 * D
    return (double)d2;
}

// Prim's algorithm to compute MST on a subset of nodes
// active_nodes: indices of nodes to include
// parent: output vector for MST structure
// adj: output adjacency list for MST
double run_prim(const vector<int>& active_nodes, vector<int>& parent, vector<vector<int>>& adj) {
    int num_total = devices.size();
    parent.assign(num_total, -1);
    adj.assign(num_total, vector<int>());
    
    if (active_nodes.empty()) return 0.0;

    // Use a dense Prim implementation O(V^2) which is efficient for V <= 3000
    // Mapping from global index to boolean for fast checking
    vector<double> min_dist(num_total, 1e18);
    vector<bool> in_tree(num_total, false);
    
    // Start from the first active node
    int start_node = active_nodes[0];
    min_dist[start_node] = 0;
    
    double total_cost = 0;
    
    // We need to add |active_nodes| vertices to the tree
    for (int i = 0; i < active_nodes.size(); ++i) {
        int u = -1;
        double best_d = 1e18;
        
        // Find closest node not yet in tree
        for (int idx : active_nodes) {
            if (!in_tree[idx] && min_dist[idx] < best_d) {
                best_d = min_dist[idx];
                u = idx;
            }
        }

        if (u == -1) break; // Should not happen if graph is connected

        in_tree[u] = true;
        total_cost += best_d;
        
        if (parent[u] != -1) {
            adj[u].push_back(parent[u]);
            adj[parent[u]].push_back(u);
        }

        // Update distances to neighbors
        for (int v : active_nodes) {
            if (!in_tree[v]) {
                // Relay stations cannot communicate with each other
                if (devices[u].type == 'C' && devices[v].type == 'C') continue;
                
                double w = get_cost(u, v);
                if (w < min_dist[v]) {
                    min_dist[v] = w;
                    parent[v] = u;
                }
            }
        }
    }
    return total_cost;
}

// Compute MST cost for a small subset of robots (used for local optimization check)
double get_subset_mst_cost(const vector<int>& subset) {
    if (subset.size() <= 1) return 0;
    
    int k = subset.size();
    vector<double> d(k, 1e18);
    vector<bool> vis(k, false);
    d[0] = 0;
    double cost = 0;
    
    for(int i=0; i<k; ++i) {
        int u = -1;
        double best = 1e18;
        for(int j=0; j<k; ++j) {
            if (!vis[j] && d[j] < best) {
                best = d[j];
                u = j;
            }
        }
        if (u == -1) break;
        vis[u] = true;
        cost += best;
        
        int u_idx = subset[u];
        for(int j=0; j<k; ++j) {
            if (!vis[j]) {
                int v_idx = subset[j];
                double w = get_cost(u_idx, v_idx);
                if (w < d[j]) d[j] = w;
            }
        }
    }
    return cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;

    devices.resize(N + K);
    for (int i = 0; i < N + K; ++i) {
        cin >> devices[i].id >> devices[i].x >> devices[i].y >> devices[i].type;
    }

    // Initially, all robots are active, and we consider all relays
    vector<int> current_relays;
    for(int i=0; i<K; ++i) current_relays.push_back(N + i);

    vector<int> active_nodes;
    vector<int> parent;
    vector<vector<int>> adj;
    
    // Iterative refinement
    // 1. Compute MST
    // 2. Prune leaves
    // 3. Local check: if a relay is costlier than connecting its neighbors directly, remove it
    for (int iter = 0; iter < 5; ++iter) {
        active_nodes.clear();
        for(int i=0; i<N; ++i) active_nodes.push_back(i);
        active_nodes.insert(active_nodes.end(), current_relays.begin(), current_relays.end());
        
        run_prim(active_nodes, parent, adj);

        // Prune degree-1 relays recursively
        vector<int> degrees(devices.size(), 0);
        vector<int> q;
        vector<bool> removed(devices.size(), false);
        
        for(int u : active_nodes) {
            degrees[u] = adj[u].size();
            if (devices[u].type == 'C' && degrees[u] <= 1) { // <= 1 to handle isolated or leaf
                q.push_back(u);
            }
        }
        
        int head = 0;
        while(head < q.size()) {
            int u = q[head++];
            removed[u] = true;
            for(int v : adj[u]) {
                if (!removed[v]) {
                    degrees[v]--;
                    if (devices[v].type == 'C' && degrees[v] == 1) {
                        q.push_back(v);
                    }
                }
            }
        }
        
        // Filter out pruned relays
        vector<int> next_relays;
        for(int r : current_relays) {
            if (!removed[r]) next_relays.push_back(r);
        }
        current_relays = next_relays;
        
        // Local Optimization Check
        vector<int> to_remove;
        for (int r : current_relays) {
            vector<int> neighbors;
            double current_local_cost = 0;
            for (int v : adj[r]) {
                if (!removed[v]) {
                    neighbors.push_back(v);
                    current_local_cost += get_cost(r, v);
                }
            }
            
            // If for some reason a relay has < 2 neighbors after pruning (shouldn't happen with correct logic), it's useless
            if (neighbors.size() < 2) {
                to_remove.push_back(r);
                continue;
            }

            // Neighbors of a relay are always Robots (since C-C is invalid)
            // Calculate cost to connect neighbors without this relay
            double alt_cost = get_subset_mst_cost(neighbors);
            
            // If direct connection is cheaper, this relay is suboptimal locally
            if (alt_cost < current_local_cost - 1e-9) {
                to_remove.push_back(r);
            }
        }
        
        if (to_remove.empty()) {
            break; // Converged
        }
        
        set<int> bad_set(to_remove.begin(), to_remove.end());
        vector<int> temp;
        for(int r : current_relays) {
            if (bad_set.find(r) == bad_set.end()) {
                temp.push_back(r);
            }
        }
        current_relays = temp;
    }
    
    // Final MST computation with selected relays
    active_nodes.clear();
    for(int i=0; i<N; ++i) active_nodes.push_back(i);
    active_nodes.insert(active_nodes.end(), current_relays.begin(), current_relays.end());
    
    run_prim(active_nodes, parent, adj);
    
    // Final pruning pass (just in case the last Prim run created leaves)
    vector<bool> final_removed(devices.size(), false);
    vector<int> degrees(devices.size(), 0);
    vector<int> q;
    
    for(int u : active_nodes) {
        degrees[u] = adj[u].size();
        if (devices[u].type == 'C' && degrees[u] <= 1) {
            q.push_back(u);
        }
    }
    int head = 0;
    while(head < q.size()) {
        int u = q[head++];
        final_removed[u] = true;
        for(int v : adj[u]) {
            if (!final_removed[v]) {
                degrees[v]--;
                if (devices[v].type == 'C' && degrees[v] == 1) {
                    q.push_back(v);
                }
            }
        }
    }

    // Output selected relay IDs
    vector<int> final_relays_ids;
    for(int r : current_relays) {
        if (!final_removed[r]) {
            final_relays_ids.push_back(devices[r].id);
        }
    }
    sort(final_relays_ids.begin(), final_relays_ids.end());
    
    if (final_relays_ids.empty()) {
        cout << "#" << endl;
    } else {
        for(size_t i=0; i<final_relays_ids.size(); ++i) {
            cout << final_relays_ids[i] << (i == final_relays_ids.size()-1 ? "" : "#");
        }
        cout << endl;
    }

    // Output edges
    bool first_edge = true;
    for (int i = 0; i < devices.size(); ++i) {
        if (final_removed[i]) continue;
        // Check edge (i, parent[i])
        if (parent[i] != -1 && !final_removed[parent[i]]) {
            if (!first_edge) cout << "#";
            cout << devices[i].id << "-" << devices[parent[i]].id;
            first_edge = false;
        }
    }
    cout << endl;

    return 0;
}
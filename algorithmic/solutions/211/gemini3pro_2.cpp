#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <queue>

using namespace std;

// Structure to store node information
struct Node {
    int id;
    long long x, y;
    char type; // 'R', 'S', 'C'
    int original_idx; 
};

int N, K;
vector<Node> nodes;

// Calculate squared Euclidean distance
double get_dist_sq(int i, int j) {
    double dx = (double)(nodes[i].x - nodes[j].x);
    double dy = (double)(nodes[i].y - nodes[j].y);
    return dx * dx + dy * dy;
}

// Calculate communication cost based on rules
double get_cost(int i, int j) {
    if (i == j) return 0.0;
    char t1 = nodes[i].type;
    char t2 = nodes[j].type;

    // Relay stations cannot communicate directly with each other
    if (t1 == 'C' && t2 == 'C') return 1e18; // Infinity

    double d2 = get_dist_sq(i, j);

    // Rule: C with any robot (R or S) is 1 * D
    // Note: The problem states "between a relay station (C) and any robot (R or S) is 1 * D".
    // This implies S's benefit does not apply to C connections.
    if (t1 == 'C' || t2 == 'C') {
        return 1.0 * d2;
    }

    // Rule: Between robots
    // If at least one is S, cost is 0.8 * D
    // Else (R-R), cost is 1.0 * D
    if (t1 == 'S' || t2 == 'S') {
        return 0.8 * d2;
    }

    // R-R
    return 1.0 * d2;
}

struct Edge {
    int u, v;
    double w;
};

// Prim's algorithm to find MST on a subset of nodes
pair<double, vector<Edge>> run_prim(const vector<int>& active_indices) {
    int n = active_indices.size();
    if (n == 0) return {0.0, {}};

    // Map local index 0..n-1 to global index in 'nodes'
    const vector<int>& idx_map = active_indices;
    
    vector<double> min_dist(n, 1e18);
    vector<int> parent(n, -1);
    vector<bool> in_tree(n, false);
    
    // Start from the first node
    min_dist[0] = 0;
    double total_cost = 0;
    vector<Edge> tree_edges;
    
    for (int i = 0; i < n; ++i) {
        int u = -1;
        double best = 1e18;
        
        // Find the node with minimum distance not yet in tree
        for (int j = 0; j < n; ++j) {
            if (!in_tree[j] && min_dist[j] < best) {
                best = min_dist[j];
                u = j;
            }
        }
        
        if (u == -1) break; // Should not happen for a connected component
        
        in_tree[u] = true;
        total_cost += best;
        if (parent[u] != -1) {
            tree_edges.push_back({idx_map[u], idx_map[parent[u]], best});
        }
        
        // Update neighbors
        int global_u = idx_map[u];
        for (int v = 0; v < n; ++v) {
            if (!in_tree[v]) {
                int global_v = idx_map[v];
                double weight = get_cost(global_u, global_v);
                if (weight < min_dist[v]) {
                    min_dist[v] = weight;
                    parent[v] = u;
                }
            }
        }
    }
    
    return {total_cost, tree_edges};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;

    vector<Node> robots;
    vector<Node> relays;

    for (int i = 0; i < N + K; ++i) {
        int id;
        long long x, y;
        char type;
        cin >> id >> x >> y >> type;
        Node node = {id, x, y, type, i};
        if (type == 'C') {
            relays.push_back(node);
        } else {
            robots.push_back(node);
        }
    }

    // Organize nodes: Robots first (0 to N-1), Relays next (N to N+K-1)
    nodes = robots;
    nodes.insert(nodes.end(), relays.begin(), relays.end());

    // 1. Calculate Base MST (only robots)
    vector<int> robot_indices(N);
    for(int i=0; i<N; ++i) robot_indices[i] = i;
    
    pair<double, vector<Edge>> base_res = run_prim(robot_indices);
    double base_cost = base_res.first;
    vector<Edge> base_edges = base_res.second;

    // 2. Calculate MST on All Nodes (Robots + Relays)
    vector<int> all_indices(N + K);
    for(int i=0; i<N+K; ++i) all_indices[i] = i;

    pair<double, vector<Edge>> full_res = run_prim(all_indices);
    vector<Edge> full_edges = full_res.second;
    
    // 3. Prune degree-1 relay nodes
    // Build adjacency for full tree
    int V = N + K;
    vector<vector<int>> adj(V);
    vector<int> degree(V, 0);
    vector<bool> active(V, true);

    for (auto& e : full_edges) {
        adj[e.u].push_back(e.v);
        adj[e.v].push_back(e.u);
        degree[e.u]++;
        degree[e.v]++;
    }

    queue<int> q;
    // Push all relays with degree 1 or 0 (isolated)
    // Relays are at indices N to N+K-1
    for (int i = N; i < N + K; ++i) {
        if (degree[i] <= 1) {
            q.push(i);
        }
    }

    while (!q.empty()) {
        int u = q.front();
        q.pop();
        
        if (!active[u]) continue;
        active[u] = false;
        
        for (int v : adj[u]) {
            if (active[v]) {
                degree[v]--;
                // If neighbor is a relay and becomes leaf, prune it
                if (nodes[v].type == 'C' && degree[v] == 1) {
                    q.push(v);
                }
            }
        }
    }
    
    // Reconstruct the pruned solution
    double pruned_cost = 0;
    vector<Edge> pruned_edges;
    vector<int> selected_relays;
    
    for (auto& e : full_edges) {
        if (active[e.u] && active[e.v]) {
            pruned_edges.push_back(e);
            pruned_cost += e.w;
        }
    }
    
    for (int i = N; i < N + K; ++i) {
        if (active[i]) {
            selected_relays.push_back(nodes[i].id);
        }
    }
    
    // 4. Compare costs and Output
    // We choose the pruned solution if it is strictly better than Base MST,
    // or if costs are equal (either is fine, usually Base is safer but pruned is valid).
    // Problem says: "If your network cost is less than or equal to the base MST cost, you receive full score."
    // So if pruned_cost <= base_cost, using pruned is optimal or equal.
    // However, floats can be tricky. We use a simple comparison.
    // Since using relays adds Steiner points, it should reduce cost. Pruning removes useless ones.
    
    vector<Edge> final_edges;
    vector<int> final_relays;
    
    if (pruned_cost <= base_cost) {
        final_edges = pruned_edges;
        final_relays = selected_relays;
    } else {
        final_edges = base_edges;
        // No relays
    }

    // Output Relay IDs
    if (final_relays.empty()) {
        cout << "#" << endl;
    } else {
        sort(final_relays.begin(), final_relays.end());
        for (size_t i = 0; i < final_relays.size(); ++i) {
            cout << final_relays[i] << (i == final_relays.size() - 1 ? "" : "#");
        }
        cout << endl;
    }
    
    // Output Links
    vector<pair<int, int>> edges_out;
    for (auto& e : final_edges) {
        int id1 = nodes[e.u].id;
        int id2 = nodes[e.v].id;
        if (id1 > id2) swap(id1, id2);
        edges_out.push_back({id1, id2});
    }
    // Sort edges for deterministic output
    sort(edges_out.begin(), edges_out.end());
    
    for (size_t i = 0; i < edges_out.size(); ++i) {
        cout << edges_out[i].first << "-" << edges_out[i].second << (i == edges_out.size() - 1 ? "" : "#");
    }
    cout << endl;

    return 0;
}
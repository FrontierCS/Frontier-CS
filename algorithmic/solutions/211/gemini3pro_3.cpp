#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <string>

using namespace std;

// Maximum number of nodes: N + K <= 3000
const int MAX_NODES = 3005;

struct Node {
    int id;           // Internal ID: 0 to N+K-1
    int original_id;  // ID given in the input
    int x, y;
    char type;        // 'R', 'S', 'C'
};

int N, K;
vector<Node> nodes;
double adj_matrix[MAX_NODES][MAX_NODES];

// Calculate squared Euclidean distance
long long distSq(const Node& a, const Node& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    return dx * dx + dy * dy;
}

// Calculate weight between two nodes based on problem rules
double calc_weight(int i, int j) {
    if (i == j) return 0;
    const Node& a = nodes[i];
    const Node& b = nodes[j];
    
    // Relay to Relay communication is forbidden
    if (a.type == 'C' && b.type == 'C') return 1e18; 
    
    long long d = distSq(a, b);
    
    if (a.type == 'C' || b.type == 'C') {
        // Relay to Robot: 1 * D
        return (double)d;
    } else {
        // Robot to Robot
        // If either is S, 0.8 * D
        if (a.type == 'S' || b.type == 'S') return 0.8 * d;
        // R to R: 1 * D
        return (double)d;
    }
}

// Compute MST cost for a subset of nodes (which are all robots)
// The subgraph of robots is a clique, so it's always connected.
double compute_subset_mst_cost(const vector<int>& subset) {
    if (subset.empty()) return 0;
    if (subset.size() == 1) return 0;
    
    int m = subset.size();
    vector<double> min_d(m, 1e18);
    vector<bool> visited(m, false);
    
    double total_cost = 0;
    min_d[0] = 0;
    
    for (int i = 0; i < m; ++i) {
        int u = -1;
        for (int j = 0; j < m; ++j) {
            if (!visited[j] && (u == -1 || min_d[j] < min_d[u])) {
                u = j;
            }
        }
        
        if (u == -1 || min_d[u] == 1e18) break; 
        visited[u] = true;
        total_cost += min_d[u];
        
        int global_u = subset[u];
        for (int v = 0; v < m; ++v) {
            if (!visited[v]) {
                int global_v = subset[v];
                double w = adj_matrix[global_u][global_v];
                if (w < min_d[v]) {
                    min_d[v] = w;
                }
            }
        }
    }
    return total_cost;
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> K)) return 0;

    nodes.resize(N + K);
    for (int i = 0; i < N + K; ++i) {
        cin >> nodes[i].original_id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
        nodes[i].id = i;
    }

    // Precompute adjacency matrix weights
    for (int i = 0; i < N + K; ++i) {
        for (int j = i; j < N + K; ++j) {
            double w = calc_weight(i, j);
            adj_matrix[i][j] = adj_matrix[j][i] = w;
        }
    }

    // Initially, all relays are candidates
    vector<bool> relay_active(N + K, false);
    for (int i = 0; i < N + K; ++i) {
        if (nodes[i].type == 'C') relay_active[i] = true;
    }

    vector<vector<int>> tree_adj(N + K);
    
    // Iterative improvement loop
    // Runs Prim's MST and removes inefficient relays
    // We limit iterations to avoid potential infinite loops and time limit, 
    // though it typically converges very fast (2-5 iterations).
    for (int iter = 0; iter < 15; ++iter) {
        vector<int> active_indices;
        active_indices.reserve(N + K);
        for (int i = 0; i < N + K; ++i) {
            if (nodes[i].type != 'C' || relay_active[i]) {
                active_indices.push_back(i);
            }
        }
        
        int m = active_indices.size();
        if (m == 0) break; 

        // Prim's Algorithm on active nodes
        vector<double> min_d(m, 1e18);
        vector<int> parent(m, -1);
        vector<bool> visited(m, false);
        
        min_d[0] = 0;
        
        // Reset adjacency list
        for(int i=0; i<N+K; ++i) tree_adj[i].clear();
        
        for (int i = 0; i < m; ++i) {
            int u = -1;
            for (int j = 0; j < m; ++j) {
                if (!visited[j] && (u == -1 || min_d[j] < min_d[u])) {
                    u = j;
                }
            }
            
            if (u == -1 || min_d[u] == 1e18) break;
            visited[u] = true;
            
            int global_u = active_indices[u];
            if (parent[u] != -1) {
                int global_p = active_indices[parent[u]];
                tree_adj[global_u].push_back(global_p);
                tree_adj[global_p].push_back(global_u);
            }
            
            for (int v = 0; v < m; ++v) {
                if (!visited[v]) {
                    int global_v = active_indices[v];
                    double w = adj_matrix[global_u][global_v];
                    if (w < min_d[v]) {
                        min_d[v] = w;
                        parent[v] = u;
                    }
                }
            }
        }
        
        // Identify inefficient relays
        vector<int> to_remove;
        for (int i = 0; i < N + K; ++i) {
            if (nodes[i].type == 'C' && relay_active[i]) {
                // If relay is a leaf (degree 1) or isolated (degree 0), it's redundant.
                // A leaf relay connects to 1 robot. Cost > 0. MST of 1 robot is 0. Thus inefficient.
                if (tree_adj[i].size() < 2) {
                    to_remove.push_back(i);
                    continue;
                }
                
                double star_cost = 0;
                for (int neighbor : tree_adj[i]) {
                    star_cost += adj_matrix[i][neighbor];
                }
                
                // Compare with MST cost of neighbors connected directly
                double alt_cost = compute_subset_mst_cost(tree_adj[i]);
                
                // If using the relay is more expensive than connecting neighbors directly, remove it.
                if (star_cost > alt_cost + 1e-7) {
                    to_remove.push_back(i);
                }
            }
        }
        
        if (to_remove.empty()) break;
        
        for (int id : to_remove) {
            relay_active[id] = false;
        }
    }
    
    // Final MST construction for output
    vector<int> active_indices;
    for (int i = 0; i < N + K; ++i) {
        if (nodes[i].type != 'C' || relay_active[i]) {
            active_indices.push_back(i);
        }
    }
    int m = active_indices.size();
    vector<double> min_d(m, 1e18);
    vector<int> parent(m, -1);
    vector<bool> visited(m, false);
    min_d[0] = 0;
    
    vector<pair<int,int>> edges;
    
    for (int i = 0; i < m; ++i) {
        int u = -1;
        for (int j = 0; j < m; ++j) {
            if (!visited[j] && (u == -1 || min_d[j] < min_d[u])) {
                u = j;
            }
        }
        if (u == -1) break;
        visited[u] = true;
        
        int global_u = active_indices[u];
        if (parent[u] != -1) {
            int global_p = active_indices[parent[u]];
            edges.push_back({global_u, global_p});
        }
        
        for (int v = 0; v < m; ++v) {
            if (!visited[v]) {
                int global_v = active_indices[v];
                double w = adj_matrix[global_u][global_v];
                if (w < min_d[v]) {
                    min_d[v] = w;
                    parent[v] = u;
                }
            }
        }
    }
    
    // Output Relays
    vector<int> used_relays;
    for (int i = 0; i < N + K; ++i) {
        if (nodes[i].type == 'C' && relay_active[i]) {
            used_relays.push_back(nodes[i].original_id);
        }
    }
    sort(used_relays.begin(), used_relays.end());
    if (used_relays.empty()) cout << "#" << endl;
    else {
        for (size_t i = 0; i < used_relays.size(); ++i) {
            cout << used_relays[i] << (i == used_relays.size() - 1 ? "" : "#");
        }
        cout << endl;
    }
    
    // Output Links
    vector<pair<int,int>> out_edges;
    for (auto& p : edges) {
        int u = nodes[p.first].original_id;
        int v = nodes[p.second].original_id;
        if (u > v) swap(u, v);
        out_edges.push_back({u, v});
    }
    sort(out_edges.begin(), out_edges.end());
    
    for (size_t i = 0; i < out_edges.size(); ++i) {
        cout << out_edges[i].first << "-" << out_edges[i].second << (i == out_edges.size() - 1 ? "" : "#");
    }
    cout << endl;

    return 0;
}
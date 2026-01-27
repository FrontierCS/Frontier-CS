#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Global constants and data
int N, M;
vector<vector<int>> adj;

// Timer setup
auto start_time = chrono::high_resolution_clock::now();
double get_elapsed() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

// Random Number Generator
mt19937 rng(1337);

// Structure to store a solution result from heuristic
struct Solution {
    int k;
    vector<int> colors;
};

// DSatur Algorithm Implementation
// Provides a good initial upper bound
Solution run_dsatur() {
    vector<int> colors(N, 0);
    // sat_deg[u] counts number of distinct colors in neighborhood of u
    vector<int> sat_deg(N + 1, 0);
    // deg[u] is static degree
    vector<int> deg(N + 1, 0);
    vector<bool> colored(N + 1, false);
    
    // Keep track of which colors are adjacent to each node
    // node_adj_colors[u][c] is true if a neighbor of u has color c
    // Note: Max colors can be N. 
    static bool node_adj_colors[505][505];
    for(int i=0; i<=N; ++i)
        for(int j=0; j<=N; ++j) node_adj_colors[i][j] = false;

    for(int i=1; i<=N; ++i) deg[i] = (int)adj[i].size();

    int uncolored_count = N;
    
    while(uncolored_count > 0) {
        // Find vertex with max saturation, break ties with degree
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;
        
        vector<int> candidates;
        
        for(int i=1; i<=N; ++i) {
            if(!colored[i]) {
                if(sat_deg[i] > max_sat) {
                    max_sat = sat_deg[i];
                    max_deg = deg[i];
                    candidates.clear();
                    candidates.push_back(i);
                } else if(sat_deg[i] == max_sat) {
                    if(deg[i] > max_deg) {
                        max_deg = deg[i];
                        candidates.clear();
                        candidates.push_back(i);
                    } else if(deg[i] == max_deg) {
                        candidates.push_back(i);
                    }
                }
            }
        }
        
        // Random tie-breaking
        uniform_int_distribution<int> dist(0, (int)candidates.size() - 1);
        best_u = candidates[dist(rng)];
        
        // Assign smallest available color
        int assigned_color = 1;
        while(true) {
            if(!node_adj_colors[best_u][assigned_color]) {
                break;
            }
            assigned_color++;
        }
        
        colors[best_u - 1] = assigned_color;
        colored[best_u] = true;
        uncolored_count--;
        
        // Update neighbors
        for(int v : adj[best_u]) {
            if(!colored[v]) {
                if(!node_adj_colors[v][assigned_color]) {
                    node_adj_colors[v][assigned_color] = true;
                    sat_deg[v]++;
                }
            }
        }
    }
    
    int max_c = 0;
    for(int c : colors) max_c = max(max_c, c);
    return {max_c, colors};
}

// Tabu Search (TabuCol) Implementation
// Tries to find a valid k-coloring. Returns true if successful.
// Updates sol_out with the valid coloring (1-based colors).
bool solve_tabu(int k, vector<int>& sol_out, double end_time) {
    // 0-based colors for internal calculation: 0 to k-1
    vector<int> col(N + 1);
    uniform_int_distribution<int> dist_k(0, k - 1);
    for(int i=1; i<=N; ++i) col[i] = dist_k(rng);
    
    // gamma[u][c] = number of neighbors of u that have color c
    static int gamma[505][505];
    for(int i=1; i<=N; ++i)
        for(int c=0; c<k; ++c) gamma[i][c] = 0;
        
    for(int u=1; u<=N; ++u) {
        for(int v : adj[u]) {
            gamma[u][col[v]]++;
        }
    }
    
    // Count conflicts
    int conflicts = 0;
    for(int u=1; u<=N; ++u) {
        conflicts += gamma[u][col[u]];
    }
    conflicts /= 2; // Each edge counted twice
    
    if (conflicts == 0) {
        for(int i=1; i<=N; ++i) sol_out[i-1] = col[i] + 1;
        return true;
    }
    
    int best_conflicts_found = conflicts;

    // Tabu Matrix: stores iteration number until which move is forbidden
    static int tabu[505][505];
    for(int i=0; i<=N; ++i)
        for(int c=0; c<k; ++c) tabu[i][c] = 0;
        
    long long iter = 0;
    vector<int> conf_nodes;
    conf_nodes.reserve(N);

    while(true) {
        iter++;
        // Time check every 256 iterations
        if ((iter & 255) == 0) {
             if (get_elapsed() > end_time) break;
        }
        
        // Build list of conflicting nodes
        conf_nodes.clear();
        for(int i=1; i<=N; ++i) {
            if(gamma[i][col[i]] > 0) conf_nodes.push_back(i);
        }
        
        if (conf_nodes.empty()) { // Should be caught by conflicts==0 check, but safe guard
            for(int i=1; i<=N; ++i) sol_out[i-1] = col[i] + 1;
            return true;
        }

        int best_delta = 1e9;
        // best_u, best_c selection logic
        // We track "best allowed" move (non-tabu or aspiration met)
        // and "best any" move (if we are forced to pick a tabu move)
        
        int best_valid_delta = 1e9;
        int best_valid_u = -1, best_valid_c = -1;
        int count_valid = 0;
        
        int best_any_delta = 1e9;
        int best_any_u = -1, best_any_c = -1;
        int count_any = 0;
        
        for(int u : conf_nodes) {
            int current_c = col[u];
            for(int c=0; c<k; ++c) {
                if(c == current_c) continue;
                
                int delta = gamma[u][c] - gamma[u][current_c];
                
                // Update best_any (in case all moves are tabu)
                if(delta < best_any_delta) {
                    best_any_delta = delta;
                    best_any_u = u;
                    best_any_c = c;
                    count_any = 1;
                } else if(delta == best_any_delta) {
                    count_any++;
                    // Reservoir sampling for random tie breaking
                    // Logic: replace with prob 1/count
                    if(uniform_int_distribution<int>(0, count_any-1)(rng) == 0) {
                        best_any_u = u;
                        best_any_c = c;
                    }
                }
                
                bool is_tabu = (tabu[u][c] >= iter);
                bool aspiration = (conflicts + delta < best_conflicts_found);
                
                if(!is_tabu || aspiration) {
                    if(delta < best_valid_delta) {
                        best_valid_delta = delta;
                        best_valid_u = u;
                        best_valid_c = c;
                        count_valid = 1;
                    } else if(delta == best_valid_delta) {
                        count_valid++;
                        if(uniform_int_distribution<int>(0, count_valid-1)(rng) == 0) {
                            best_valid_u = u;
                            best_valid_c = c;
                        }
                    }
                }
            }
        }
        
        // Select move
        int u_move = -1, c_move = -1, move_delta = 0;
        
        if(best_valid_u != -1) {
            u_move = best_valid_u;
            c_move = best_valid_c;
            move_delta = best_valid_delta;
        } else {
            // Forced move: take best tabu move
            if(best_any_u != -1) {
                u_move = best_any_u;
                c_move = best_any_c;
                move_delta = best_any_delta;
            } else {
                // Deadlock or no moves (unlikely with conflicts)
                // Just random restart this iteration on a node
                u_move = conf_nodes[uniform_int_distribution<int>(0, (int)conf_nodes.size()-1)(rng)];
                c_move = uniform_int_distribution<int>(0, k-1)(rng);
                if(c_move == col[u_move]) c_move = (c_move + 1) % k;
                move_delta = gamma[u_move][c_move] - gamma[u_move][col[u_move]];
            }
        }
        
        // Apply move
        int old_c = col[u_move];
        col[u_move] = c_move;
        conflicts += move_delta;
        
        if(conflicts < best_conflicts_found) best_conflicts_found = conflicts;
        
        // Update neighbors' gamma
        for(int v : adj[u_move]) {
            gamma[v][old_c]--;
            gamma[v][c_move]++;
        }
        
        // Update Tabu tenure
        // Heuristic: 0.6 * number_of_conflicts + random
        int tenure = (int)(0.6 * conf_nodes.size()) + (uniform_int_distribution<int>(0, 9)(rng));
        tabu[u_move][old_c] = iter + tenure;
        
        if(conflicts == 0) {
            for(int i=1; i<=N; ++i) sol_out[i-1] = col[i] + 1;
            return true;
        }
    }
    
    return false;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    adj.resize(N + 1);
    for(int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if(u != v) { // constraints say distinct, but safety check
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }
    
    // Sort and unique adjacency lists to handle multiple edges properly
    for(int i=1; i<=N; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    // Step 1: Initial solution using DSatur
    // Run multiple iterations in the first 0.15s to get a good starting point
    Solution best_sol;
    best_sol.k = N + 1;
    
    // Ensure we run at least once
    best_sol = run_dsatur();
    
    while(get_elapsed() < 0.15) {
        Solution sol = run_dsatur();
        if(sol.k < best_sol.k) {
            best_sol = sol;
        }
    }
    
    // Step 2: Tabu Search to minimize K
    // We attempt to solve for target_k = best_sol.k - 1, then - 2, ...
    int target_k = best_sol.k - 1;
    vector<int> final_colors = best_sol.colors;
    
    while(target_k >= 2) { // Minimum colors is 1 (if no edges) or 2 (if bipartite)
        vector<int> temp_colors(N);
        // Time budget: stop searching at 1.95s absolute time
        if(solve_tabu(target_k, temp_colors, 1.95)) {
            // Found a valid coloring with target_k
            final_colors = temp_colors;
            target_k--;
        } else {
            // Could not find solution in time or iterations
            break;
        }
        
        if(get_elapsed() > 1.90) break;
    }
    
    // Output result
    for(int c : final_colors) {
        cout << c << "\n";
    }
    
    return 0;
}
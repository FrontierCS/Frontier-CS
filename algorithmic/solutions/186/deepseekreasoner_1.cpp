#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Global variables for graph and coloring state
int N, M;
vector<vector<int>> adj;
vector<int> final_colors;
int best_k = 1e9;
double start_time;

// Tabu Search specific structures to avoid reallocation
vector<vector<int>> adj_color_table;
vector<int> current_colors;
vector<int> conflicting_nodes;
vector<bool> in_conflict_set;
vector<vector<int>> tabu_status;
int total_conflicts;

// Time utility to respect the 2.0s limit
double get_time() {
    return (double)(clock() - start_time) / CLOCKS_PER_SEC;
}

// DSATUR Heuristic to obtain a good initial coloring
void solve_dsatur() {
    vector<int> degree(N);
    for(int i=0; i<N; ++i) degree[i] = adj[i].size();
    
    vector<int> sat(N, 0);
    vector<int> colors(N, 0);
    vector<bool> colored(N, false);
    // adj_has_color[u][c] is true if vertex u has a neighbor with color c
    vector<vector<bool>> adj_has_color(N, vector<bool>(N + 1, false));
    
    int colored_cnt = 0;
    while(colored_cnt < N) {
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;
        
        // Select vertex with max saturation, break ties with max degree
        for(int i=0; i<N; ++i) {
            if(!colored[i]) {
                if(sat[i] > max_sat) {
                    max_sat = sat[i];
                    max_deg = degree[i];
                    best_u = i;
                } else if(sat[i] == max_sat) {
                    if(degree[i] > max_deg) {
                        max_deg = degree[i];
                        best_u = i;
                    }
                }
            }
        }
        
        if (best_u == -1) break; // Should not happen given logic
        
        // Find smallest valid color
        int c = 1;
        while(true) {
            if(c < (int)adj_has_color[best_u].size() && adj_has_color[best_u][c]) {
                c++;
            } else {
                break;
            }
        }
        // Ensure adj_has_color is large enough (though N+1 init covers max possible)
        if(c >= (int)adj_has_color[best_u].size()) {
            // This case ideally doesn't happen with N+1 size unless c > N
            colors[best_u] = c; 
        } else {
            colors[best_u] = c;
        }
        
        colored[best_u] = true;
        colored_cnt++;
        
        // Update neighbors' saturation info
        for(int v : adj[best_u]) {
            if(!colored[v]) {
                if(c < (int)adj_has_color[v].size() && !adj_has_color[v][c]) {
                    adj_has_color[v][c] = true;
                    sat[v]++;
                }
            }
        }
    }
    
    final_colors = colors;
    int max_c = 0;
    for(int c : colors) max_c = max(max_c, c);
    best_k = max_c;
}

// Tabu Search (TabuCol) algorithm to try and find a valid k-coloring
bool run_tabu(int k) {
    current_colors.assign(N, 1);
    
    // Initialize current_colors: 
    // Keep consistent colors from best solution found so far where possible,
    // otherwise assign random color in range [1, k].
    for(int i=0; i<N; ++i) {
        if(final_colors[i] <= k) current_colors[i] = final_colors[i];
        else current_colors[i] = 1 + rand() % k;
    }
    
    // Reset data structures for Tabu Search
    for(int i=0; i<N; ++i) {
        tabu_status[i].assign(k + 1, 0);
        for(int c=1; c<=k; ++c) adj_color_table[i][c] = 0;
    }
    
    conflicting_nodes.clear();
    in_conflict_set.assign(N, false);
    total_conflicts = 0;
    
    // Build adjacency color table and identify conflicts
    for(int u=0; u<N; ++u) {
        for(int v : adj[u]) {
            adj_color_table[u][current_colors[v]]++;
        }
    }
    
    for(int u=0; u<N; ++u) {
        if(adj_color_table[u][current_colors[u]] > 0) {
            total_conflicts += adj_color_table[u][current_colors[u]];
            conflicting_nodes.push_back(u);
            in_conflict_set[u] = true;
        }
    }
    total_conflicts /= 2; // Each edge counted twice
    
    if(total_conflicts == 0) return true;
    
    long long iter = 0;
    
    // Run search until time cutoff
    while(true) {
        // Time check every 2048 iterations to minimize overhead
        if((iter & 2047) == 0) {
            if(get_time() > 1.95) return false;
        }
        
        // Lazy cleaning of conflicting_nodes vector
        for(int i=0; i<(int)conflicting_nodes.size(); ++i) {
            int u = conflicting_nodes[i];
            if(adj_color_table[u][current_colors[u]] == 0) {
                in_conflict_set[u] = false;
                conflicting_nodes[i] = conflicting_nodes.back();
                conflicting_nodes.pop_back();
                i--;
            }
        }
        
        if(conflicting_nodes.empty()) return true;
        
        int best_delta = 1e9;
        vector<pair<int, int>> candidates; 
        
        // Evaluate moves for vertices currently in conflict
        for(int u : conflicting_nodes) {
            int c_old = current_colors[u];
            int current_confl = adj_color_table[u][c_old];
            
            // Try changing to every other color
            for(int c = 1; c <= k; ++c) {
                if(c == c_old) continue;
                
                int delta = adj_color_table[u][c] - current_confl;
                
                // Tabu status check
                bool is_tabu = (tabu_status[u][c] > iter);
                
                // Aspiration criterion: if move solves all conflicts (unlikely in one step unless close)
                // or simply if tabu, we skip unless it leads to 0 global conflicts.
                if(is_tabu && (total_conflicts + delta > 0)) {
                    continue;
                }
                
                if(delta < best_delta) {
                    best_delta = delta;
                    candidates.clear();
                    candidates.push_back({u, c});
                } else if(delta == best_delta) {
                    candidates.push_back({u, c});
                }
            }
        }
        
        if(candidates.empty()) {
            // All moves Tabu? Just advance iteration counter
            iter++; 
            continue;
        }
        
        // Pick a random best move to diversify
        pair<int, int> move = candidates[rand() % candidates.size()];
        int u = move.first;
        int c_new = move.second;
        int c_old = current_colors[u];
        
        // Apply move
        current_colors[u] = c_new;
        total_conflicts += best_delta;
        
        // Update neighbor info
        for(int v : adj[u]) {
            adj_color_table[v][c_old]--;
            adj_color_table[v][c_new]++;
            // If v becomes a conflict node, add it
            if(adj_color_table[v][current_colors[v]] > 0 && !in_conflict_set[v]) {
                in_conflict_set[v] = true;
                conflicting_nodes.push_back(v);
            }
        }
        
        // Set Tabu tenure: dynamic based on number of conflicts + random noise
        int tenure = (int)(conflicting_nodes.size()) * 0.6 + (rand() % 10) + 4;
        tabu_status[u][c_old] = iter + tenure;
        
        if(total_conflicts == 0) return true;
        iter++;
    }
    return false;
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    start_time = clock();
    srand(1337); // Deterministic seed for consistency
    
    if (!(cin >> N >> M)) return 0;
    
    adj.resize(N);
    for(int i=0; i<M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // 0-based indexing
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Step 1: Get initial solution using DSATUR
    solve_dsatur();
    
    // Step 2: Try to improve solution (reduce k) using Tabu Search
    // Pre-allocate memory for Tabu structures
    adj_color_table.resize(N, vector<int>(N + 1));
    tabu_status.resize(N);
    
    // While we have time and can potentially reduce colors
    while(best_k > 1 && get_time() < 1.95) {
        int target_k = best_k - 1;
        if(run_tabu(target_k)) {
            best_k = target_k;
            final_colors = current_colors;
            // Success, loop continues to try even fewer colors
        } else {
            // Could not find solution with target_k colors within time
            break; 
        }
    }
    
    // Output result
    for(int i=0; i<N; ++i) {
        cout << final_colors[i] << "\n";
    }
    
    return 0;
}
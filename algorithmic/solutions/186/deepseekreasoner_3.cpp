#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <set>
#include <random>
#include <chrono>
#include <cstring>

using namespace std;

const int MAXN = 505;
int N, M;
vector<int> neighbors[MAXN];

// Solution state
int optimal_k = 1e9;
vector<int> optimal_coloring;

// For timing
auto start_time = chrono::high_resolution_clock::now();

double get_elapsed() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

// DSATUR Heuristic to get an initial good solution
void run_dsatur() {
    vector<int> coloring(N + 1, 0);
    vector<int> sat_degree(N + 1, 0);
    vector<int> uncolored_degree(N + 1, 0);
    vector<bool> colored(N + 1, false);
    
    for (int i = 1; i <= N; ++i) {
        uncolored_degree[i] = neighbors[i].size();
    }

    int colored_count = 0;
    while (colored_count < N) {
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;

        for (int i = 1; i <= N; ++i) {
            if (!colored[i]) {
                if (sat_degree[i] > max_sat) {
                    max_sat = sat_degree[i];
                    max_deg = uncolored_degree[i];
                    best_u = i;
                } else if (sat_degree[i] == max_sat) {
                    if (uncolored_degree[i] > max_deg) {
                        max_deg = uncolored_degree[i];
                        best_u = i;
                    }
                }
            }
        }

        int u = best_u;
        colored[u] = true;
        colored_count++;

        // Find smallest available color
        vector<bool> used(N + 1, false);
        for (int v : neighbors[u]) {
            if (colored[v]) {
                used[coloring[v]] = true;
            }
        }

        int assigned_color = 1;
        while (used[assigned_color]) assigned_color++;
        coloring[u] = assigned_color;

        // Update saturation for neighbors
        for (int v : neighbors[u]) {
            if (!colored[v]) {
                uncolored_degree[v]--; 
                bool seen = false;
                for(int w : neighbors[v]) {
                    if (colored[w] && coloring[w] == assigned_color && w != u) {
                        seen = true;
                        break;
                    }
                }
                if (!seen) {
                    sat_degree[v]++;
                }
            }
        }
    }

    // Save result if better
    int max_c = 0;
    for (int i = 1; i <= N; ++i) max_c = max(max_c, coloring[i]);
    
    if (max_c < optimal_k) {
        optimal_k = max_c;
        optimal_coloring = coloring;
    }
}

// Tabu Search structures
int gamma_adj[MAXN][MAXN]; // gamma_adj[u][c] = number of neighbors of u with color c
int current_colors[MAXN];
int tabu_list[MAXN][MAXN]; // tabu_list[u][c] = iter at which it stops being tabu
long long iter_cnt = 0;

// Tabu Search for k-coloring
// Returns true if k-coloring found
bool solve_tabu(int K) {
    mt19937 rng(1337 + iter_cnt);
    
    // Initialize random coloring with K colors
    for(int i=1; i<=N; ++i) {
        current_colors[i] = (rng() % K) + 1;
    }

    // Initialize gamma and count conflicts
    for(int i=1; i<=N; ++i) {
        for(int c=1; c<=K; ++c) {
            gamma_adj[i][c] = 0;
        }
    }
    
    int conflicts = 0;
    for(int u=1; u<=N; ++u) {
        for(int v : neighbors[u]) {
            if(u < v) {
                if(current_colors[u] == current_colors[v]) {
                    conflicts++;
                }
            }
            gamma_adj[u][current_colors[v]]++;
        }
    }
    
    // Reset Tabu
    for(int i=0; i<=N; ++i)
        for(int c=0; c<=K; ++c) tabu_list[i][c] = 0;
        
    iter_cnt = 0;
    // Iteration limit based on time mostly
    int max_iter_check = 10000; 

    while(true) {
        if (conflicts == 0) return true;
        
        if ((iter_cnt % 2000) == 0) {
            if (get_elapsed() > 1.96) return false;
            // A hard iteration limit per call to allow restarts can be useful
            if (iter_cnt > 2000000) return false;
        }
        
        iter_cnt++;
        
        int best_delta = 1e9;
        int best_u = -1;
        int best_c = -1;
        int num_equal = 0;

        // Collect conflicting nodes
        vector<int> conflict_nodes;
        for(int i=1; i<=N; ++i) {
            if (gamma_adj[i][current_colors[i]] > 0) {
                conflict_nodes.push_back(i);
            }
        }
        
        if (conflict_nodes.empty() && conflicts > 0) {
            // Should not happen, recalculate triggers
             conflicts = 0;
             for(int u=1; u<=N; ++u) 
               if(gamma_adj[u][current_colors[u]] > 0) {
                   conflicts += gamma_adj[u][current_colors[u]];
               }
             conflicts /= 2;
             if (conflicts == 0) return true;
        }

        // Find best non-tabu move or aspiration move
        for (int u : conflict_nodes) {
            int current_c = current_colors[u];
            int current_penalty = gamma_adj[u][current_c]; 
            
            for (int c = 1; c <= K; ++c) {
                if (c == current_c) continue;
                
                int delta = gamma_adj[u][c] - current_penalty;
                
                // Aspiration
                if (conflicts + delta == 0) {
                    best_u = u;
                    best_c = c;
                    goto perform_move;
                }
                
                if (tabu_list[u][c] <= iter_cnt) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                        num_equal = 1;
                    } else if (delta == best_delta) {
                        num_equal++;
                        if ((rng() % num_equal) == 0) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                }
            }
        }
        
        // If no valid non-tabu move found (entire neighborhood tabu), pick best tabu
        if (best_u == -1) {
             int best_delta_tabu = 1e9;
             for (int u : conflict_nodes) {
                int current_c = current_colors[u];
                int current_penalty = gamma_adj[u][current_c];
                for (int c = 1; c <= K; ++c) {
                    if (c == current_c) continue;
                    int delta = gamma_adj[u][c] - current_penalty;
                    if (delta < best_delta_tabu) {
                        best_delta_tabu = delta;
                        best_u = u;
                        best_c = c;
                        num_equal = 1;
                    } else if (delta == best_delta_tabu) {
                        num_equal++;
                        if ((rng() % num_equal) == 0) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                }
            }
        }
        
perform_move:
        if (best_u != -1) {
            int old_c = current_colors[best_u];
            int new_c = best_c;
            
            current_colors[best_u] = new_c;
            
            int delta_conf = gamma_adj[best_u][new_c] - gamma_adj[best_u][old_c];
            conflicts += delta_conf;
            
            for (int v : neighbors[best_u]) {
                gamma_adj[v][old_c]--;
                gamma_adj[v][new_c]++;
            }
            
            int tenure = 7 + (rng() % 10) + (int)(0.6 * conflict_nodes.size()); 
            tabu_list[best_u][old_c] = iter_cnt + tenure;
        } 
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        neighbors[u].push_back(v);
        neighbors[v].push_back(u);
    }

    optimal_k = N + 1;
    run_dsatur();
    
    while (get_elapsed() < 1.96) {
        int target_k = optimal_k - 1;
        if (target_k < 1) break; 
        
        bool success = false;
        // Allows restarts
        for(int r=0; r < 20; ++r) {
            if(get_elapsed() > 1.96) break; 
            if(solve_tabu(target_k)) {
                success = true;
                break;
            }
        }
        
        if (success) {
            optimal_k = target_k;
            for(int i=1; i<=N; ++i) optimal_coloring[i] = current_colors[i];
        } else {
            // If failed repeatedly, probably stuck at optimum K
            // Continue trying until time out in case stochastic search finds something
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << optimal_coloring[i] << "\n";
    }

    return 0;
}
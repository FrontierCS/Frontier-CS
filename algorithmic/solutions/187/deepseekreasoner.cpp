#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Global variables
int N, M;
bool adj[505][505]; // Adjacency matrix for graph G
vector<int> adj_bar[505]; // Adjacency list for complement graph G_bar

// Best solution found
vector<int> best_coloring;
int best_k = 1000;

// Timing
clock_t start_time_clock;

double get_elapsed_time() {
    return (double)(clock() - start_time_clock) / CLOCKS_PER_SEC;
}

// DSatur initialization
void run_dsatur() {
    vector<int> colors(N + 1, 0);
    vector<int> sat_deg(N + 1, 0);
    vector<int> deg_uncolored(N + 1, 0);
    vector<bool> colored(N + 1, false);
    
    // Degree in G_bar
    for (int i = 1; i <= N; ++i) deg_uncolored[i] = adj_bar[i].size();
    
    // Matrix to track adjacent colors
    static bool neighbor_has_color[505][505];
    for(int i=1; i<=N; ++i) for(int j=1; j<=N; ++j) neighbor_has_color[i][j] = false;
    
    for (int i = 0; i < N; ++i) {
        int u = -1, max_sat = -1, max_deg = -1;
        
        for (int v = 1; v <= N; ++v) {
            if (!colored[v]) {
                if (sat_deg[v] > max_sat) {
                    max_sat = sat_deg[v];
                    max_deg = deg_uncolored[v];
                    u = v;
                } else if (sat_deg[v] == max_sat) {
                    if (deg_uncolored[v] > max_deg) {
                        max_deg = deg_uncolored[v];
                        u = v;
                    }
                }
            }
        }
        
        if (u == -1) break; // Should not happen
        colored[u] = true;
        
        int c = 1;
        while (c <= N && neighbor_has_color[u][c]) c++;
        colors[u] = c;
        
        for (int v : adj_bar[u]) {
            if (!colored[v]) {
                if (!neighbor_has_color[v][c]) {
                    neighbor_has_color[v][c] = true;
                    sat_deg[v]++;
                }
                deg_uncolored[v]--;
            }
        }
    }
    
    int k = 0;
    for(int i=1; i<=N; ++i) k = max(k, colors[i]);
    
    if (k < best_k) {
        best_k = k;
        best_coloring.resize(N);
        for(int i=1; i<=N; ++i) best_coloring[i-1] = colors[i];
    }
}

// Tabu Search structures
int K_target;
vector<int> current_sol;
int conflict_matrix[505][505]; // [vertex][color]
int tabu_tensor[505][505]; // [vertex][color] -> iter
int current_conflicts = 0;

void build_minimize_structures() {
    for(int i=1; i<=N; ++i) {
        for(int c=1; c<=K_target; ++c) {
            conflict_matrix[i][c] = 0;
            tabu_tensor[i][c] = 0; // reset tabu
        }
    }
    current_conflicts = 0;
    
    for (int u = 1; u <= N; ++u) {
        for (int v : adj_bar[u]) {
            conflict_matrix[u][current_sol[v-1]]++;
        }
    }
    
    for (int u = 1; u <= N; ++u) {
        current_conflicts += conflict_matrix[u][current_sol[u-1]];
    }
    current_conflicts /= 2;
}

void solve_tabu() {
    // Random init
    current_sol.resize(N);
    for(int i=0; i<N; ++i) current_sol[i] = (rand() % K_target) + 1;
    
    build_minimize_structures();
    
    if (current_conflicts == 0) return;
    
    int iter = 0;
    
    while (true) {
        iter++;
        if ((iter & 1023) == 0) {
            if (get_elapsed_time() > 1.96) return;
        }
        
        int best_u = -1;
        int best_c = -1;
        int best_delta = 1000000;
        
        // Collect conflicting nodes
        static vector<int> conflicting_nodes;
        conflicting_nodes.clear();
        for(int i=1; i<=N; ++i) {
             if (conflict_matrix[i][current_sol[i-1]] > 0) 
                 conflicting_nodes.push_back(i);
        }
        
        if (conflicting_nodes.empty()) {
             current_conflicts = 0; 
             return; 
        }

        for (int u : conflicting_nodes) {
            int old_c = current_sol[u-1];
            int current_penalty = conflict_matrix[u][old_c];
            
            for (int c = 1; c <= K_target; ++c) {
                if (c == old_c) continue;
                
                int delta = conflict_matrix[u][c] - current_penalty;
                
                // Aspiration
                if (current_conflicts + delta == 0) {
                    best_u = u; best_c = c; best_delta = delta;
                    goto apply_move;
                }
                
                bool is_tabu = (tabu_tensor[u][c] >= iter);
                if (!is_tabu) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                    } else if (delta == best_delta) {
                        if (rand() % 2) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                }
            }
        }
        
        if (best_u == -1) {
            // All beneficial/neutral moves Tabu. Pick a random move to escape
            if (!conflicting_nodes.empty()) {
                int idx = rand() % conflicting_nodes.size();
                best_u = conflicting_nodes[idx];
                do {
                    best_c = (rand() % K_target) + 1;
                } while (best_c == current_sol[best_u-1]);
                best_delta = conflict_matrix[best_u][best_c] - conflict_matrix[best_u][current_sol[best_u-1]];
            } else {
                return; // Should be handled by empty check above
            }
        }
        
        apply_move:
        int u = best_u;
        int old_c = current_sol[u-1];
        int new_c = best_c;
        current_sol[u-1] = new_c;
        current_conflicts += best_delta;
        
        for (int v : adj_bar[u]) {
            conflict_matrix[v][old_c]--;
            conflict_matrix[v][new_c]++;
        }
        
        // Tabu tenure
        int tenure = (int)(0.6 * current_conflicts) + (rand() % 10);
        tabu_tensor[u][old_c] = iter + tenure;
        
        if (current_conflicts == 0) return;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    start_time_clock = clock();
    srand(1337);
    
    if (!(cin >> N >> M)) return 0;
    
    for(int i=0; i<M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u][v] = adj[v][u] = true;
    }
    
    // Complement graph
    for(int i=1; i<=N; ++i) {
        for(int j=1; j<=N; ++j) {
            if (i != j && !adj[i][j]) {
                adj_bar[i].push_back(j);
            }
        }
    }
    
    run_dsatur();
    
    while (get_elapsed_time() < 1.96 && best_k > 1) {
        K_target = best_k - 1;
        
        solve_tabu();
        
        bool ok = true;
        for(int i=1; i<=N; ++i) {
            for (int neighbor : adj_bar[i]) {
                if (current_sol[i-1] == current_sol[neighbor-1]) {
                    ok = false;
                    break;
                }
            }
            if(!ok) break;
        }
        
        if (ok) {
            best_k = K_target;
            best_coloring = current_sol;
        }
    }
    
    for(int i=0; i<N; ++i) {
        cout << best_coloring[i] << "\n";
    }
    
    return 0;
}
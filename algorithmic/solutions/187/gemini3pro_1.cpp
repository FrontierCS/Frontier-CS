#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <ctime>
#include <cstdlib>
#include <cstring>
#include <random>

using namespace std;

// Constants
const int MAXN = 505;
const double TIME_LIMIT = 1.95; 

// Global variables
int N, M;
bool adj[MAXN][MAXN]; // Adjacency matrix for G
vector<int> adj_bar[MAXN]; // Adjacency list for Complement Graph G_bar

// Solution tracking
int best_k = MAXN;
vector<int> best_solution(MAXN);

// Tabu search state
int color[MAXN];
int adj_colors[MAXN][MAXN]; // [u][c] = count of neighbors of u in G_bar having color c
int conflicts = 0;
int tabu[MAXN][MAXN]; // Tabu tenure

// RNG
mt19937 rng(1337);

double get_time() {
    return (double)clock() / CLOCKS_PER_SEC;
}

// Greedy heuristic to find initial solution
int greedy_coloring(vector<int>& result_colors) {
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);
    
    fill(result_colors.begin(), result_colors.end(), 0);
    int max_c = 0;
    
    vector<int> used(N + 2);
    
    for (int u : p) {
        fill(used.begin(), used.end(), 0);
        for (int v : adj_bar[u]) {
            if (result_colors[v] != 0) {
                used[result_colors[v]] = 1;
            }
        }
        int c = 1;
        while (used[c]) c++;
        result_colors[u] = c;
        if (c > max_c) max_c = c;
    }
    return max_c;
}

void build_adjacency() {
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (!adj[i][j]) {
                adj_bar[i].push_back(j);
                adj_bar[j].push_back(i);
            }
        }
    }
}

// TabuCol algorithm to find a valid k-coloring
bool solve_k_coloring(int k, int max_iter) {
    // Random initialization
    for (int i = 1; i <= N; ++i) {
        color[i] = (rng() % k) + 1;
    }

    // Init adj_colors and conflicts
    for (int i = 1; i <= N; ++i) {
        for (int c = 1; c <= k; ++c) adj_colors[i][c] = 0;
    }
    
    for (int u = 1; u <= N; ++u) {
        for (int v : adj_bar[u]) {
            adj_colors[u][color[v]]++;
        }
    }
    
    conflicts = 0;
    for (int u = 1; u <= N; ++u) {
        conflicts += adj_colors[u][color[u]];
    }
    conflicts /= 2;

    if (conflicts == 0) return true;

    // Reset tabu
    for (int i = 0; i <= N; ++i)
        for (int j = 0; j <= k; ++j)
            tabu[i][j] = 0;

    vector<int> conflicting_nodes;
    conflicting_nodes.reserve(N);

    for (int iter = 0; iter < max_iter; ++iter) {
        // Time check occasionally
        if ((iter & 511) == 0 && get_time() > TIME_LIMIT) return false;
        
        if (conflicts == 0) return true;
        
        conflicting_nodes.clear();
        for (int i = 1; i <= N; ++i) {
            if (adj_colors[i][color[i]] > 0) {
                conflicting_nodes.push_back(i);
            }
        }
        
        if (conflicting_nodes.empty()) return true; // Should ideally be caught by conflicts==0

        int best_delta = 1e9;
        int best_u = -1;
        int best_c = -1;
        
        // Iterate over conflicting nodes to find best move
        for (int u : conflicting_nodes) {
            int current_c = color[u];
            int current_penalty = adj_colors[u][current_c];
            
            for (int c = 1; c <= k; ++c) {
                if (c == current_c) continue;
                
                int delta = adj_colors[u][c] - current_penalty;
                
                // Aspiration
                if (conflicts + delta == 0) {
                    best_u = u; best_c = c; best_delta = delta;
                    goto apply_move;
                }
                
                if (tabu[u][c] <= iter) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                    } else if (delta == best_delta) {
                        if ((rng() & 1) == 0) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                }
            }
        }
        
        // If no non-tabu move found, or trapped, pick random conflicting
        if (best_u == -1) {
             best_u = conflicting_nodes[rng() % conflicting_nodes.size()];
             best_c = (rng() % k) + 1;
             while (best_c == color[best_u]) best_c = (rng() % k) + 1;
             best_delta = adj_colors[best_u][best_c] - adj_colors[best_u][color[best_u]];
        }
        
        apply_move:
        int old_c = color[best_u];
        color[best_u] = best_c;
        conflicts += best_delta;
        
        for (int v : adj_bar[best_u]) {
            adj_colors[v][old_c]--;
            adj_colors[v][best_c]++;
        }
        
        // Tabu tenure: 7 + random(5) + 0.6*conflicts
        int tenure = 7 + (int)(0.6 * conflicts) + (rng() % 5);
        tabu[best_u][old_c] = iter + tenure; 
    }
    
    return conflicts == 0;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    memset(adj, 0, sizeof(adj));
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u][v] = adj[v][u] = true;
    }
    
    build_adjacency();
    
    // Initial Greedy Solutions
    vector<int> current_sol(N + 1);
    for (int i = 0; i < 50; ++i) {
        int k = greedy_coloring(current_sol);
        if (k < best_k) {
            best_k = k;
            copy(current_sol.begin(), current_sol.end(), best_solution.begin());
        }
        if (get_time() > 0.3) break; 
    }
    
    // Optimization loop
    while (best_k > 1 && get_time() < TIME_LIMIT) {
        int target_k = best_k - 1;
        bool success = false;
        
        int attempts = 0;
        // Try multiple times for the same k if time permits
        while (!success && get_time() < TIME_LIMIT && attempts < 50) {
            success = solve_k_coloring(target_k, 25000); 
            if (success) {
                best_k = target_k;
                for (int i = 1; i <= N; ++i) best_solution[i] = color[i];
            }
            attempts++;
        }
        
        if (!success) break; // Cannot reduce K further
    }
    
    for (int i = 1; i <= N; ++i) {
        cout << best_solution[i] << "\n";
    }
    
    return 0;
}
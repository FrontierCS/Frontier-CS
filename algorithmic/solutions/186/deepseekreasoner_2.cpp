#include <iostream>
#include <vector>
#include <algorithm>
#include <set>
#include <random>
#include <chrono>
#include <cstring>
#include <iomanip>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 505;
const double TIME_LIMIT = 1.95; // 2.0s limit, stop slightly early

int N, M;
// Adjacency representations
bool adj[MAXN][MAXN];
vector<int> adj_list[MAXN];
int degree[MAXN];

// Store the best solution found so far
int best_k = MAXN;
vector<int> best_colors(MAXN);

// Timer
auto start_time = chrono::high_resolution_clock::now();

double get_elapsed() {
    auto current_time = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = current_time - start_time;
    return diff.count();
}

// DSatur Algorithm to generate an initial greedy solution
void run_dsatur() {
    vector<int> saturation(N + 1, 0);
    vector<int> uncolored_degree(N + 1);
    vector<int> colors(N + 1, 0);
    vector<bool> colored(N + 1, false);
    
    // adj_color_table[u][c] stores how many neighbors of u have color c
    static int adj_color_table[MAXN][MAXN]; 
    memset(adj_color_table, 0, sizeof(adj_color_table));

    for (int i = 1; i <= N; ++i) uncolored_degree[i] = degree[i];

    for (int i = 0; i < N; ++i) {
        int u = -1;
        int max_sat = -1;
        int max_deg = -1;

        // Choice heuristic: max saturation, then max uncolored degree
        for (int v = 1; v <= N; ++v) {
            if (!colored[v]) {
                if (saturation[v] > max_sat) {
                    max_sat = saturation[v];
                    max_deg = uncolored_degree[v];
                    u = v;
                } else if (saturation[v] == max_sat) {
                    if (uncolored_degree[v] > max_deg) {
                        max_deg = uncolored_degree[v];
                        u = v;
                    }
                }
            }
        }

        if (u == -1) break;

        // Assign smallest available color
        int c = 1;
        while (adj_color_table[u][c] > 0) c++;

        colors[u] = c;
        colored[u] = true;

        // Update neighbors
        for (int v : adj_list[u]) {
            if (!colored[v]) {
                uncolored_degree[v]--;
                // If this is the first neighbor of v with color c, increment saturation
                if (adj_color_table[v][c] == 0) {
                    saturation[v]++;
                }
                adj_color_table[v][c]++;
            }
        }
    }

    int current_k = 0;
    for (int i = 1; i <= N; ++i) current_k = max(current_k, colors[i]);

    if (current_k < best_k) {
        best_k = current_k;
        best_colors = colors;
    }
}

// Variables for Tabu Search
int sol[MAXN];
int tabu_list[MAXN][MAXN]; // Stores the iteration number until which move is tabu
int adj_color_count[MAXN][MAXN]; // [u][c] count of neighbors of u with color c

// Update helper structure when u changes color
void perform_move(int u, int c_new, int c_old) {
    sol[u] = c_new;
    for (int v : adj_list[u]) {
        adj_color_count[v][c_old]--;
        adj_color_count[v][c_new]++;
    }
}

// Rebuild helper structure
void rebuild_gamma(int k) {
    for (int i = 1; i <= N; ++i) {
        for (int c = 1; c <= k; ++c) {
            adj_color_count[i][c] = 0;
        }
    }
    for (int u = 1; u <= N; ++u) {
        for (int v : adj_list[u]) {
            if (sol[v] >= 1 && sol[v] <= k)
                adj_color_count[u][sol[v]]++;
        }
    }
}

// Tabu Search to find a valid k-coloring
bool solve_tabu(int k) {
    // Seed depends on something dynamic to allow restarts to be different
    mt19937 rng(1337 + k + (int)(get_elapsed() * 100000));
    
    // Initialize solution: Keep colors 1..k from best solution,
    // map colors > k to random 1..k
    for (int i = 1; i <= N; ++i) {
        if (best_colors[i] <= k) sol[i] = best_colors[i];
        else sol[i] = (rng() % k) + 1;
    }
    
    rebuild_gamma(k);
    
    int current_conflicts = 0;
    for (int i = 1; i <= N; ++i) {
        current_conflicts += adj_color_count[i][sol[i]];
    }
    current_conflicts /= 2; // Each edge counted twice

    if (current_conflicts == 0) return true;

    // Reset tabu table
    for(int i = 1; i <= N; ++i) 
        for(int c = 1; c <= k; ++c) tabu_list[i][c] = 0;
        
    int iter = 0;
    int min_conflicts = current_conflicts; // Best conflicts seen in this run
    
    // Heuristic parameters
    const int tabu_tenure_base = 7; 
    
    while (true) {
        iter++;
        // Check time limit occasionally
        if ((iter & 2047) == 0) {
            if (get_elapsed() > TIME_LIMIT) return false;
        }
        
        int best_delta = 1e9;
        int best_u = -1, best_c = -1;
        
        int best_tabu_delta = 1e9;
        int best_tabu_u = -1, best_tabu_c = -1;
        
        // Identify conflicting nodes to narrow search space
        vector<int> conflicting;
        conflicting.reserve(N);
        for (int i = 1; i <= N; ++i) {
            if (adj_color_count[i][sol[i]] > 0) conflicting.push_back(i);
        }
        
        if (conflicting.empty()) return true;

        for (int u : conflicting) {
            int current_c = sol[u];
            int current_u_conflicts = adj_color_count[u][current_c];
            
            for (int c = 1; c <= k; ++c) {
                if (c == current_c) continue;
                
                int delta = adj_color_count[u][c] - current_u_conflicts;
                
                bool is_tabu = (tabu_list[u][c] >= iter);
                
                // Aspiration criterion: override tabu if it leads to a new best state
                if (is_tabu) {
                    if (current_conflicts + delta < min_conflicts) {
                        is_tabu = false;
                    }
                }
                
                if (!is_tabu) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                    } else if (delta == best_delta) {
                        // Tie breaking
                        if (rng() % 2) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                } else {
                    if (delta < best_tabu_delta) {
                        best_tabu_delta = delta;
                        best_tabu_u = u;
                        best_tabu_c = c;
                    } 
                }
            }
        }
        
        int u_move = -1, c_move = -1, delta_move = 0;
        
        // Select logic: best non-tabu, else best tabu
        if (best_u != -1) {
            u_move = best_u;
            c_move = best_c;
            delta_move = best_delta;
        } else if (best_tabu_u != -1) {
            u_move = best_tabu_u;
            c_move = best_tabu_c;
            delta_move = best_tabu_delta;
        } else {
            // No moves possible? Should not happen. Backtrack or restart.
            return false;
        }
        
        // Execute move
        int old_c = sol[u_move];
        perform_move(u_move, c_move, old_c);
        current_conflicts += delta_move;
        
        if (current_conflicts < min_conflicts) min_conflicts = current_conflicts;
        if (current_conflicts == 0) return true;
        
        // Update Tabu Tenure
        // Dynamic tenure dependent on number of conflicts to manage diversification/intensification
        int tenure_val = tabu_tenure_base + (int)(0.6 * conflicting.size()) + (rng() % 10);
        tabu_list[u_move][old_c] = iter + tenure_val;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    
    memset(adj, 0, sizeof(adj));
    memset(degree, 0, sizeof(degree));
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v && !adj[u][v]) {
            adj[u][v] = adj[v][u] = true;
            adj_list[u].push_back(v);
            adj_list[v].push_back(u);
            degree[u]++;
            degree[v]++;
        }
    }
    
    // Step 1: Greedy init
    run_dsatur();
    
    // Step 2: Iteratively try to find better coloring
    while (get_elapsed() < TIME_LIMIT) {
        int target_k = best_k - 1;
        if (target_k < 1) break;
        
        // Run Tabu Search to see if target_k coloring exists
        if (solve_tabu(target_k)) {
            best_k = target_k;
            for (int i = 1; i <= N; ++i) best_colors[i] = sol[i];
        } else {
            // If failed, the loop continues and solve_tabu will be called again
            // with a potentially different random initialization
        }
    }

    for (int i = 1; i <= N; ++i) {
        cout << best_colors[i] << "\n";
    }

    return 0;
}
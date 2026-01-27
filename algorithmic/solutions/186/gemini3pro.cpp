#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <numeric>
#include <cstring>
#include <random>

using namespace std;

// Global variables
int N, M;
vector<vector<int>> adj;
vector<int> best_coloring;
int best_colors_count = 1e9;
double start_time;

// Helper function to check elapsed time
double get_time() {
    return (double)(clock() - start_time) / CLOCKS_PER_SEC;
}

// Fast Randomized Greedy Algorithm
// Generates a valid coloring and updates global best if improved
void run_greedy() {
    static vector<int> p;
    if (p.empty()) {
        p.resize(N);
        iota(p.begin(), p.end(), 1);
    }
    
    // Shuffle vertices to get random greedy order
    for (int i = N - 1; i > 0; --i) {
        int j = rand() % (i + 1);
        swap(p[i], p[j]);
    }

    vector<int> coloring(N + 1, 0);
    int max_c = 0;
    
    // Optimization: used[c] stores the iteration ID when color c was last marked forbidden
    static vector<int> used(505, 0);
    static int iter_cnt = 0;

    for (int u : p) {
        iter_cnt++;
        for (int v : adj[u]) {
            if (coloring[v] != 0) {
                if (coloring[v] < 505)
                    used[coloring[v]] = iter_cnt;
            }
        }
        int c = 1;
        while (used[c] == iter_cnt) c++;
        coloring[u] = c;
        if (c > max_c) max_c = c;
    }

    if (max_c < best_colors_count) {
        best_colors_count = max_c;
        best_coloring = coloring;
    }
}

// Tabu Search (TabuCol) to find a valid k-coloring
// Returns true if a valid k-coloring is found, false otherwise
bool solve_tabu(int k) {
    // Current coloring (1-based), initialized randomly
    vector<int> coloring(N + 1);
    for(int i=1; i<=N; ++i) coloring[i] = 1 + rand() % k;
    
    // adj_color_count[u][c]: number of neighbors of u with color c
    static int adj_color_count[505][505]; 
    memset(adj_color_count, 0, sizeof(adj_color_count));
    
    // Fill adj_color_count based on initial coloring
    for (int u = 1; u <= N; ++u) {
        for (int v : adj[u]) {
            adj_color_count[u][coloring[v]]++;
        }
    }

    // conflicts[u]: number of neighbors of u with the same color as u
    vector<int> conflicts(N + 1, 0);
    int total_conflicts = 0;
    
    for (int u = 1; u <= N; ++u) {
        conflicts[u] = adj_color_count[u][coloring[u]];
        total_conflicts += conflicts[u];
    }
    total_conflicts /= 2; // Each edge counted twice

    if (total_conflicts == 0) {
        best_coloring = coloring;
        best_colors_count = k;
        return true;
    }

    // Tabu matrix: tabu[u][c] stores the iteration number until u cannot be assigned color c
    static int tabu[505][505]; 
    memset(tabu, 0, sizeof(tabu));

    long long iter = 0;
    const int MAX_ITER = 5000000; // Large limit, controlled by time mainly

    while (iter < MAX_ITER) {
        // Check time limit every 4096 iterations
        if ((iter & 0xFFF) == 0) { 
            if (get_time() > 1.98) return false;
        }
        iter++;

        int best_delta = 1e9;
        int best_u = -1;
        int best_c = -1;
        int count_best = 0;
        
        // Dynamic tabu tenure
        int tenure = 10 + (rand() % 10);
        
        // Scan for best move among conflicting vertices
        for (int u = 1; u <= N; ++u) {
            if (conflicts[u] == 0) continue; 
            
            int current_c = coloring[u];
            int current_conflicts_u = adj_color_count[u][current_c];
            
            for (int c = 1; c <= k; ++c) {
                if (c == current_c) continue;
                
                // Calculate change in total conflicts (delta)
                int delta = adj_color_count[u][c] - current_conflicts_u;
                
                // Aspiration Criteria: if this move solves the problem, accept immediately
                if (total_conflicts + delta == 0) {
                    best_u = u; best_c = c;
                    goto apply_move; 
                }
                
                // Check if move is Tabu
                if (tabu[u][c] >= iter) continue;
                
                // Pick best non-tabu move
                if (delta < best_delta) {
                    best_delta = delta;
                    best_u = u;
                    best_c = c;
                    count_best = 1;
                } else if (delta == best_delta) {
                    count_best++;
                    // Reservoir sampling for randomness
                    if ((rand() % count_best) == 0) {
                        best_u = u;
                        best_c = c;
                    }
                }
            }
        }

        if (best_u == -1) {
            // No valid non-tabu moves found (should be rare with aspiration)
            // Break to trigger restart
            break;
        }

        apply_move:
        int u = best_u;
        int old_c = coloring[u];
        int new_c = best_c;
        
        // Update total conflicts
        int delta = adj_color_count[u][new_c] - adj_color_count[u][old_c];
        total_conflicts += delta;
        coloring[u] = new_c;
        
        // Update conflicts for u
        conflicts[u] = adj_color_count[u][new_c];
        
        // Update neighbors
        for (int v : adj[u]) {
            adj_color_count[v][old_c]--;
            adj_color_count[v][new_c]++;
            
            if (coloring[v] == old_c) conflicts[v]--;
            else if (coloring[v] == new_c) conflicts[v]++;
        }
        
        // Make moving back to old color Tabu
        tabu[u][old_c] = iter + tenure;
        
        if (total_conflicts == 0) {
            best_coloring = coloring;
            best_colors_count = k;
            return true;
        }
    }
    
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    start_time = clock();
    srand(1337); // Fixed seed for reproducibility

    if (!(cin >> N >> M)) return 0;

    adj.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Phase 1: Fast Greedy to establish an upper bound
    // Run for a short duration (0.1s) to get a good starting point
    while (get_time() < 0.1) {
        run_greedy();
    }
    
    // Phase 2: Tabu Search optimization
    // Try to reduce the number of colors k one by one
    int k = best_colors_count - 1;
    
    while (k >= 1 && get_time() < 1.98) {
        bool success = false;
        
        // Allow multiple restarts for the same k
        int restarts = 0;
        while(get_time() < 1.98) {
             if (solve_tabu(k)) {
                 success = true;
                 break;
             } else {
                 restarts++;
                 // Heuristic: if we fail too many times for a specific k, it's likely too hard
                 if (restarts > 20) break; 
             }
        }
        
        if (success) {
            k--; // Try fewer colors
        } else {
            // Could not improve further
            break;
        }
    }

    // Output the best solution found
    for (int i = 1; i <= N; ++i) {
        cout << best_coloring[i] << "\n";
    }

    return 0;
}
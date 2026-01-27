#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

const int MAXN = 505;
int N, M;
// Adjacency matrix and list for the complement graph G_bar
bool adj[MAXN][MAXN];
vector<int> adj_list[MAXN];
int degree[MAXN];

// Best solution found
int best_k;
vector<int> best_colors;

// Working state for Tabu Search
vector<int> current_colors;
int adj_color_count[MAXN][MAXN]; // [u][c]: number of neighbors of u with color c
int tabu[MAXN][MAXN];
int pos_in_conflicted[MAXN];
vector<int> conflicted_nodes;

double get_time() {
    return (double)clock() / CLOCKS_PER_SEC;
}

void add_conflicted(int u) {
    if (pos_in_conflicted[u] == -1) {
        pos_in_conflicted[u] = (int)conflicted_nodes.size();
        conflicted_nodes.push_back(u);
    }
}

void remove_conflicted(int u) {
    if (pos_in_conflicted[u] != -1) {
        int last = conflicted_nodes.back();
        int pos = pos_in_conflicted[u];
        conflicted_nodes[pos] = last;
        pos_in_conflicted[last] = pos;
        conflicted_nodes.pop_back();
        pos_in_conflicted[u] = -1;
    }
}

void update_status(int u) {
    if (adj_color_count[u][current_colors[u]] > 0) add_conflicted(u);
    else remove_conflicted(u);
}

// DSatur heuristic to generate initial solution
void dsatur() {
    vector<int> result(N + 1, 0);
    vector<int> sat_deg(N + 1, 0);
    vector<int> uncolored_deg(N + 1, 0);
    vector<bool> colored(N + 1, false);
    
    for (int i = 1; i <= N; ++i) uncolored_deg[i] = degree[i];

    for (int count = 0; count < N; ++count) {
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;

        for (int i = 1; i <= N; ++i) {
            if (!colored[i]) {
                if (sat_deg[i] > max_sat) {
                    max_sat = sat_deg[i];
                    max_deg = uncolored_deg[i];
                    best_u = i;
                } else if (sat_deg[i] == max_sat) {
                    if (uncolored_deg[i] > max_deg) {
                        max_deg = uncolored_deg[i];
                        best_u = i;
                    }
                }
            }
        }

        int u = best_u;
        colored[u] = true;
        
        vector<bool> used_c(N + 1, false);
        for (int v : adj_list[u]) {
            if (colored[v]) {
                if (result[v] <= N) used_c[result[v]] = true;
            }
        }
        int c = 1;
        while (c <= N && used_c[c]) c++;
        result[u] = c;

        for (int v : adj_list[u]) {
            if (!colored[v]) {
                uncolored_deg[v]--;
                bool seen = false;
                for (int w : adj_list[v]) {
                    if (colored[w] && result[w] == c && w != u) {
                        seen = true;
                        break;
                    }
                }
                if (!seen) sat_deg[v]++;
            }
        }
    }

    int max_c = 0;
    for (int i = 1; i <= N; ++i) max_c = max(max_c, result[i]);
    best_k = max_c;
    best_colors = result;
}

// Tabu search to try and find a valid k-coloring
bool solve_k(int k, double time_limit) {
    // Initialization
    for (int i = 1; i <= N; ++i) {
        for (int c = 1; c <= k; ++c) adj_color_count[i][c] = 0;
        for (int c = 1; c <= k; ++c) tabu[i][c] = 0;
        pos_in_conflicted[i] = -1;
    }
    conflicted_nodes.clear();
    current_colors.assign(N + 1, 0);

    // Random initial coloring
    for (int i = 1; i <= N; ++i) current_colors[i] = 1 + rand() % k;

    // Compute conflict counts
    for (int u = 1; u <= N; ++u) {
        for (int v : adj_list[u]) {
            adj_color_count[u][current_colors[v]]++;
        }
    }
    
    int total_conflicts = 0;
    for (int i = 1; i <= N; ++i) {
        update_status(i);
        total_conflicts += adj_color_count[i][current_colors[i]];
    }
    total_conflicts /= 2;

    if (total_conflicts == 0) return true;

    long long iter = 0;
    int min_conflicts = total_conflicts;

    // Optimization loop
    while (iter < 50000000) { 
        if ((iter & 4095) == 0) {
            if (get_time() > time_limit) return false;
        }
        iter++;
        
        if (conflicted_nodes.empty()) return true;

        // Pick a random vertex involved in a conflict
        int u = conflicted_nodes[rand() % conflicted_nodes.size()];
        int old_c = current_colors[u];
        int conflicts_u = adj_color_count[u][old_c];
        
        int best_c = -1;
        int best_delta = 1e9;
        
        vector<int> candidates;
        
        // Try all other colors
        for (int c = 1; c <= k; ++c) {
            if (c == old_c) continue;
            int delta = adj_color_count[u][c] - conflicts_u;
            
            // Aspiration criterion
            if (total_conflicts + delta < min_conflicts) {
                if (delta < best_delta) {
                    best_delta = delta;
                    best_c = c;
                    candidates.clear();
                    candidates.push_back(c);
                } else if (delta == best_delta) {
                    candidates.push_back(c);
                }
            } else {
                // Tabu check
                if (tabu[u][c] <= iter) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_c = c;
                        candidates.clear();
                        candidates.push_back(c);
                    } else if (delta == best_delta) {
                        candidates.push_back(c);
                    }
                }
            }
        }
        
        if (candidates.empty()) {
            continue;
        }
        
        // Randomly select one of the best moves
        int move_c = candidates[rand() % candidates.size()];
        
        // Apply move
        current_colors[u] = move_c;
        total_conflicts += best_delta;
        if (total_conflicts < min_conflicts) min_conflicts = total_conflicts;
        
        if (total_conflicts == 0) return true;
        
        // Update neighbors
        for (int v : adj_list[u]) {
            adj_color_count[v][old_c]--;
            adj_color_count[v][move_c]++;
            update_status(v);
        }
        update_status(u);
        
        // Set tabu tenure
        int tenure = 7 + (int)(0.6 * total_conflicts) + (rand() % 10);
        tabu[u][old_c] = (int)iter + tenure;
    }
    
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    // Construct complement graph G_bar
    // Initialize adj with true (complete graph)
    for (int i = 1; i <= N; ++i) {
        for (int j = 1; j <= N; ++j) {
            adj[i][j] = (i != j);
        }
    }
    // Remove edges that exist in G
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u][v] = adj[v][u] = false;
    }
    // Build adjacency list for G_bar
    for (int i = 1; i <= N; ++i) {
        degree[i] = 0;
        for (int j = 1; j <= N; ++j) {
            if (adj[i][j]) {
                adj_list[i].push_back(j);
                degree[i]++;
            }
        }
    }
    
    srand((unsigned)time(NULL) + 12345);
    
    // Get initial valid coloring
    dsatur();
    
    // Attempt to reduce the number of cliques (colors in G_bar)
    double time_limit = 1.96; 
    while (best_k > 1 && get_time() < time_limit) {
        if (solve_k(best_k - 1, time_limit)) {
            best_k--;
            best_colors = current_colors;
        } else {
            break;
        }
    }
    
    // Output the result
    for (int i = 1; i <= N; ++i) {
        cout << best_colors[i] << "\n";
    }
    
    return 0;
}
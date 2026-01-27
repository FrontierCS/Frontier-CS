#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

const int MAXN = 505;
const double TIME_LIMIT = 1.98;

int N, M;
bool adj_mat[MAXN][MAXN];
vector<int> adj_bar[MAXN];

// Best Solution Found
int best_k;
vector<int> best_colors;

// Working Solution
vector<int> current_colors;

// Tabu Search Data Structures
int conflict_counts[MAXN][MAXN]; // [node][color] -> count of neighbors with color
int tabu_tenure[MAXN][MAXN];     // [node][color] -> iter until tabu
int nodes_conflicts[MAXN];       // [node] -> count of conflict edges incident to node
int total_conflicts_count = 0;   // Total edges in conflict

mt19937 rng(1337);
chrono::time_point<chrono::steady_clock> start_time;

// Build Complement Graph G_bar
// Edge in G_bar <-> No Edge in G
void build_complement() {
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (!adj_mat[i][j]) { // No edge in G
                adj_bar[i].push_back(j);
                adj_bar[j].push_back(i);
            }
        }
    }
}

// Grease coloring on G_bar (Minimize colors = Maximize Cliques in G is wrong, 
// we want to Partition V into Cliques equivalent to Coloring G_bar)
// DSATUR Heuristic
void dsatur() {
    vector<int> degrees(N + 1, 0);
    for (int i = 1; i <= N; ++i) degrees[i] = adj_bar[i].size();
    
    vector<int> colors(N + 1, 0);
    vector<int> sat_deg(N + 1, 0); // Saturation degree
    vector<bool> colored(N + 1, false);
    // Track colors used by neighbors: [node][color]
    vector<vector<bool>> neighbor_colors(N + 1, vector<bool>(N + 1, false));

    for (int i = 0; i < N; ++i) {
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;

        // Select uncolored vertex with max saturation degree
        for (int u = 1; u <= N; ++u) {
            if (!colored[u]) {
                if (sat_deg[u] > max_sat) {
                    max_sat = sat_deg[u];
                    max_deg = degrees[u];
                    best_u = u;
                } else if (sat_deg[u] == max_sat) {
                    if (degrees[u] > max_deg) {
                        max_deg = degrees[u];
                        best_u = u;
                    }
                }
            }
        }

        if (best_u == -1) break;

        // Assign smallest available color
        int c = 1;
        while (c < N + 1 && neighbor_colors[best_u][c]) {
            c++;
        }

        colors[best_u] = c;
        colored[best_u] = true;

        // Update neighbors
        for (int v : adj_bar[best_u]) {
            if (!colored[v]) {
                if (!neighbor_colors[v][c]) {
                    neighbor_colors[v][c] = true;
                    sat_deg[v]++;
                }
                degrees[v]--; // Decrement degree in uncolored subgraph
            }
        }
    }

    int k = 0;
    for (int i = 1; i <= N; ++i) k = max(k, colors[i]);
    best_colors = colors;
    best_k = k;
}

// Initialize Tabu Search for a target number of cliques/colors k
void init_tabu(int k) {
    current_colors.assign(N + 1, 0);
    
    // Initial assignment: Keep valid colors <= k, random otherwise
    for (int u = 1; u <= N; ++u) {
        if (best_colors[u] <= k) {
            current_colors[u] = best_colors[u];
        } else {
            current_colors[u] = (rng() % k) + 1;
        }
    }

    // Reset counts
    total_conflicts_count = 0;
    for(int i = 0; i <= N; ++i) {
        nodes_conflicts[i] = 0;
        for(int c = 0; c <= N; ++c) {
            conflict_counts[i][c] = 0;
            tabu_tenure[i][c] = 0;
        }
    }
    
    // Compute conflicts
    // Conflict exists if u and v adjacent in G_bar have same color
    for (int u = 1; u <= N; ++u) {
        for (int v : adj_bar[u]) {
            conflict_counts[u][current_colors[v]]++;
        }
    }

    for (int u = 1; u <= N; ++u) {
        int c = current_colors[u];
        nodes_conflicts[u] = conflict_counts[u][c];
        total_conflicts_count += nodes_conflicts[u];
    }
    // Each edge counted twice
    total_conflicts_count /= 2;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    start_time = chrono::steady_clock::now();

    if (!(cin >> N >> M)) return 0;
    
    // Default false
    for (int i = 1; i <= N; ++i)
        for (int j = 1; j <= N; ++j)
            adj_mat[i][j] = false;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        // Edge in G
        adj_mat[u][v] = adj_mat[v][u] = true;
    }

    // Graph G complement construction
    build_complement();
    
    // Initial Heuristic
    dsatur();
    
    // Try to improve solution by reducing K (Tabu Search)
    int target_k = best_k - 1;
    vector<int> active_conflicts;

    while (target_k > 0) {
        auto now = chrono::steady_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() > TIME_LIMIT) break;

        init_tabu(target_k);
        if (total_conflicts_count == 0) {
            // Lucky init
            best_colors = current_colors;
            best_k = target_k;
            target_k--;
            continue;
        }

        bool success = false;
        long long iter = 0;
        
        while (true) {
            iter++;
            if ((iter & 1023) == 0) {
                if ((chrono::steady_clock::now() - start_time).count() > TIME_LIMIT) break;
            }

            // Identify nodes involved in conflicts
            active_conflicts.clear();
            for(int i = 1; i <= N; ++i) {
                if(nodes_conflicts[i] > 0) active_conflicts.push_back(i);
            }

            if (active_conflicts.empty()) {
                if (total_conflicts_count == 0) {
                    success = true;
                    break;
                }
                // Should not happen
                break;
            }

            // Pick a conflicting node to move
            // Random selection from conflicting set is a simple effective strategy
            int u = active_conflicts[rng() % active_conflicts.size()];
            
            int best_node = -1;
            int best_new_color = -1;
            int best_delta = 1e9;
            
            int old_c = current_colors[u];
            
            // Try changing u to all other colors
            for (int c = 1; c <= target_k; ++c) {
                if (c == old_c) continue;
                
                // Calculate delta in total conflicts
                // Neighbors with color c become conflicts (+), with old_c resolved (-)
                int d = conflict_counts[u][c] - conflict_counts[u][old_c];
                
                // Aspiration criterion: if it leads to 0 conflicts (or better than global best), ignore tabu
                if (total_conflicts_count + d <= 0) {
                    best_node = u;
                    best_new_color = c;
                    best_delta = d;
                    goto apply_move;
                }
                
                // If not tabu, consider it
                if (tabu_tenure[u][c] < iter) {
                    if (d < best_delta) {
                        best_delta = d;
                        best_node = u;
                        best_new_color = c;
                    } else if (d == best_delta) {
                        // Tie break randomly
                        if (rng() % 2) {
                            best_node = u;
                            best_new_color = c;
                        }
                    }
                }
            }
            
            // If no non-tabu move found, perform a random walk or best tabu?
            // Simple random walk helps escape local optima
            if (best_node == -1) {
                 int rc = (rng() % target_k) + 1;
                 while (rc == old_c && target_k > 1) rc = (rng() % target_k) + 1;
                 best_node = u;
                 best_new_color = rc;
                 best_delta = conflict_counts[u][rc] - conflict_counts[u][old_c];
            }

            apply_move:
            int node = best_node;
            int nc = best_new_color;
            int oc = current_colors[node];
            
            current_colors[node] = nc;
            total_conflicts_count += best_delta;
            
            // Set tabu tenure
            int tenure = 10 + (int)nodes_conflicts[node] + (rng() % 10);
            tabu_tenure[node][oc] = iter + tenure;
            
            // Update neighbor structures
            for(int v : adj_bar[node]) {
                conflict_counts[v][oc]--;
                conflict_counts[v][nc]++;
                if (current_colors[v] == oc) nodes_conflicts[v]--;
                if (current_colors[v] == nc) nodes_conflicts[v]++;
            }
            nodes_conflicts[node] = conflict_counts[node][nc];

            if (total_conflicts_count == 0) {
                success = true;
                break;
            }
        }

        if (success) {
            best_colors = current_colors;
            best_k = target_k;
            target_k--;
        } else {
            // Time limit or stuck
            break;
        }
    }

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_colors[i] << "\n";
    }

    return 0;
}
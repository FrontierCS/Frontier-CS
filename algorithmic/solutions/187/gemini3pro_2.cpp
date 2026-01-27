#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <ctime>
#include <cstdlib>
#include <cstring>
#include <chrono>

using namespace std;

// Maximum number of vertices
const int MAXN = 505;
int N, M;
// Adjacency matrix of G
bool adjG[MAXN][MAXN];
// Adjacency list of Complement Graph (G_bar)
vector<int> adjBar[MAXN];

// Best solution found so far
int best_k = MAXN + 1;
vector<int> best_sol;

// Timer
auto start_time = chrono::high_resolution_clock::now();

double get_elapsed() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

// DSATUR Heuristic to get an initial valid coloring on G_bar
void run_dsatur() {
    vector<int> color(N + 1, 0);
    vector<int> sat(N + 1, 0);
    vector<int> deg(N + 1, 0);
    vector<bool> colored(N + 1, false);
    
    // Compute degrees in G_bar
    for (int i = 1; i <= N; ++i) {
        deg[i] = adjBar[i].size();
    }
    
    // adj_colors[u][c] is true if u has a neighbor with color c
    static bool adj_colors[MAXN][MAXN]; 
    for(int i=0; i<=N; ++i) memset(adj_colors[i], 0, sizeof(adj_colors[i]));

    for (int i = 0; i < N; ++i) {
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;
        
        // Select vertex with max saturation degree, tie-break with degree in uncolored subgraph
        for (int u = 1; u <= N; ++u) {
            if (!colored[u]) {
                if (sat[u] > max_sat) {
                    max_sat = sat[u];
                    max_deg = deg[u];
                    best_u = u;
                } else if (sat[u] == max_sat) {
                    if (deg[u] > max_deg) {
                        max_deg = deg[u];
                        best_u = u;
                    }
                }
            }
        }
        
        if (best_u == -1) break; 
        
        // Assign smallest available color
        int c = 1;
        while (adj_colors[best_u][c]) {
            c++;
        }
        
        color[best_u] = c;
        colored[best_u] = true;
        
        // Update neighbors' saturation info
        for (int v : adjBar[best_u]) {
            if (!colored[v]) {
                if (!adj_colors[v][c]) {
                    adj_colors[v][c] = true;
                    sat[v]++;
                }
                deg[v]--; 
            }
        }
    }
    
    int k = 0;
    for (int i = 1; i <= N; ++i) k = max(k, color[i]);
    
    if (k < best_k) {
        best_k = k;
        best_sol = color;
    }
}

// Tabu Search to attempt finding a valid k-coloring
// Returns true if successful
bool solve_k(int k, double time_limit) {
    vector<int> color(N + 1);
    
    // Initialization: Merge two smallest color classes from best_sol if possible
    bool used_heuristic = false;
    if (!best_sol.empty() && best_k == k + 1) {
        vector<int> counts(best_k + 1, 0);
        for(int i=1; i<=N; ++i) counts[best_sol[i]]++;
        
        vector<pair<int,int>> sorted_counts;
        for(int c=1; c<=best_k; ++c) {
            if(counts[c] > 0) sorted_counts.push_back({counts[c], c});
        }
        sort(sorted_counts.begin(), sorted_counts.end());
        
        if (sorted_counts.size() >= 2) {
            used_heuristic = true;
            int c1 = sorted_counts[0].second;
            int c2 = sorted_counts[1].second;
            
            vector<int> map_color(best_k + 1);
            int current = 1; 
            map_color[c1] = 0; // Merge into color 0
            map_color[c2] = 0; // Merge into color 0
            for(size_t i=2; i<sorted_counts.size(); ++i) {
                map_color[sorted_counts[i].second] = current++;
            }
            
            for(int i=1; i<=N; ++i) {
                color[i] = map_color[best_sol[i]];
            }
        }
    }

    // Fallback to random initialization
    if (!used_heuristic) {
        for (int i = 1; i <= N; ++i) {
            color[i] = rand() % k;
        }
    }
    
    // gamma[u][c] = number of neighbors of u with color c
    static int gamma[MAXN][MAXN]; 
    for(int i=1; i<=N; ++i)
        for(int c=0; c<k; ++c) gamma[i][c] = 0;

    int conflicts = 0;
    
    // Build gamma matrix and conflict count
    for (int u = 1; u <= N; ++u) {
        for (int v : adjBar[u]) {
            gamma[u][color[v]]++;
        }
    }
    
    for (int u = 1; u <= N; ++u) {
        conflicts += gamma[u][color[u]];
    }
    conflicts /= 2;
    
    if (conflicts == 0) {
        best_k = k;
        for(int i=1; i<=N; ++i) best_sol[i] = color[i] + 1;
        return true;
    }
    
    // Tabu Matrix
    static int tabu[MAXN][MAXN]; 
    for(int i=0; i<=N; ++i) 
        for(int j=0; j<N; ++j) tabu[i][j] = 0;
        
    long long iter = 0;
    vector<int> conf_nodes;
    conf_nodes.reserve(N);
    
    // Tabu Search Loop
    while (get_elapsed() < time_limit) {
        iter++;
        
        // Identify conflicting nodes
        conf_nodes.clear();
        for (int u = 1; u <= N; ++u) {
            if (gamma[u][color[u]] > 0) {
                conf_nodes.push_back(u);
            }
        }
        
        if (conf_nodes.empty()) {
             best_k = k;
             for(int i=1; i<=N; ++i) best_sol[i] = color[i] + 1;
             return true;
        }

        int best_delta = 1e9;
        int best_u = -1;
        int best_c = -1;
        int cnt_ties = 0;
        
        // Scan neighbors of conflicting nodes for best move
        for (int u : conf_nodes) {
            int current_c = color[u];
            int current_conflicts_u = gamma[u][current_c];
            
            for (int c = 0; c < k; ++c) {
                if (c == current_c) continue;
                
                int delta = gamma[u][c] - current_conflicts_u;
                
                bool is_tabu = (tabu[u][c] >= iter);
                // Aspiration criterion: allow tabu move if it leads to 0 conflicts
                if (is_tabu && (conflicts + delta == 0)) is_tabu = false;
                
                if (!is_tabu) {
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                        cnt_ties = 1;
                    } else if (delta == best_delta) {
                        cnt_ties++;
                        if (rand() % cnt_ties == 0) {
                            best_u = u;
                            best_c = c;
                        }
                    }
                }
            }
        }
        
        // If all improving/equal moves are tabu, force best move
        if (best_u == -1) {
             for (int u : conf_nodes) {
                int current_c = color[u];
                int current_conflicts_u = gamma[u][current_c];
                for (int c = 0; c < k; ++c) {
                    if (c == current_c) continue;
                    int delta = gamma[u][c] - current_conflicts_u;
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_u = u;
                        best_c = c;
                        cnt_ties = 1;
                    } else if (delta == best_delta) {
                        cnt_ties++;
                        if (rand() % cnt_ties == 0) {
                             best_u = u;
                             best_c = c;
                        }
                    }
                }
            }
        }
        
        if (best_u == -1) break; 
        
        // Apply move
        int old_c = color[best_u];
        color[best_u] = best_c;
        conflicts += best_delta;
        
        // Update neighbor gamma values
        for (int v : adjBar[best_u]) {
            gamma[v][old_c]--;
            gamma[v][best_c]++;
        }
        
        // Set tabu tenure
        int tenure = 7 + rand() % 10 + (int)(0.6 * conflicts);
        tabu[best_u][old_c] = iter + tenure;
        
        if (conflicts == 0) {
            best_k = k;
            for(int i=1; i<=N; ++i) best_sol[i] = color[i] + 1;
            return true;
        }
    }
    
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(NULL));
    
    if (!(cin >> N >> M)) return 0;
    
    // Initialize adjacency matrix for G
    for(int i=0; i<=N; ++i) memset(adjG[i], 0, sizeof(adjG[i]));
    
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adjG[u][v] = adjG[v][u] = true;
    }
    
    // Construct Complement Graph G_bar
    // Vertices u, v adjacent in G_bar iff not adjacent in G (and u != v)
    for (int i = 1; i <= N; ++i) {
        for (int j = i + 1; j <= N; ++j) {
            if (!adjG[i][j]) {
                adjBar[i].push_back(j);
                adjBar[j].push_back(i);
            }
        }
    }
    
    // Get initial solution using DSATUR
    run_dsatur();
    
    // Try to reduce the number of colors (cliques) using Tabu Search
    // We try to solve for K-1, K-2, ... until time runs out
    while (get_elapsed() < 1.95) {
        if (best_k <= 1) break; 
        
        // Use all remaining time for the current target k
        if (!solve_k(best_k - 1, 1.98)) {
            break;
        }
    }
    
    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_sol[i] << "\n";
    }
    
    return 0;
}
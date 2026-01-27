#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <ctime>
#include <cstring>

using namespace std;

// Time limit slightly less than 2.0s to allow output time
const double TIME_LIMIT = 1.95;

int N, M;
// Adjacency for Complement Graph G_bar
// adj_indices stores neighbors for fast iteration
// adj_deg stores degree in complement graph
// adj_mat_bar allows O(1) adjacency check in complement graph
int adj_indices[505][505];
int adj_deg[505];
bool adj_mat_bar[505][505];

// Best valid solution found so far
int best_sol[505];
int min_k;

// Tabu Search State
int color[505];
// gamma_mat[u][c] stores the number of neighbors of u (in G_bar) that have color c
int gamma_mat[505][505];
// tabu[u][c] stores the iteration number until which assigning color c to vertex u is tabu
int tabu[505][505];
// Conflict management
bool in_conflict[505];
vector<int> conflict_list;
int pos_in_list[505];
long long iter_cnt = 0;

mt19937 rng(1337);

inline int fast_rand(int ub) {
    if (ub <= 0) return 0;
    return rng() % ub;
}

void build_graph() {
    if (!(cin >> N >> M)) return;
    
    // Read Original Graph G
    static bool adj_G[505][505];
    memset(adj_G, 0, sizeof(adj_G));
    for (int i = 0; i < N; ++i) adj_G[i][i] = true; 
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        adj_G[u][v] = adj_G[v][u] = true;
    }
    
    // Build Complement Graph G_bar
    memset(adj_deg, 0, sizeof(adj_deg));
    memset(adj_mat_bar, 0, sizeof(adj_mat_bar));
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (!adj_G[i][j]) {
                adj_mat_bar[i][j] = true;
                adj_indices[i][adj_deg[i]++] = j;
            }
        }
    }
}

// DSatur Heuristic to find an initial valid clique cover (coloring of G_bar)
void run_dsatur() {
    vector<int> c(N, 0);
    vector<int> sat(N, 0);
    vector<int> deg(N);
    vector<bool> colored(N, false);
    for(int i = 0; i < N; ++i) deg[i] = adj_deg[i];
    
    int processed = 0;
    while(processed < N) {
        int best_u = -1, max_sat = -1, max_deg = -1;
        for(int i = 0; i < N; ++i) {
            if(!colored[i]) {
                if(sat[i] > max_sat || (sat[i] == max_sat && deg[i] > max_deg)) {
                    max_sat = sat[i];
                    max_deg = deg[i];
                    best_u = i;
                }
            }
        }
        
        int u = best_u;
        colored[u] = true;
        
        // Find smallest available color
        static int used_tag[505]; 
        static int tag_counter = 0;
        tag_counter++;
        
        for(int i = 0; i < adj_deg[u]; ++i) {
            int v = adj_indices[u][i];
            if(colored[v]) used_tag[c[v]] = tag_counter;
        }
        
        int chosen = 1;
        while(used_tag[chosen] == tag_counter) chosen++;
        c[u] = chosen;
        
        // Update neighbors' saturation degrees
        for(int i = 0; i < adj_deg[u]; ++i) {
            int v = adj_indices[u][i];
            if(!colored[v]) {
                deg[v]--;
                bool known = false;
                for(int j = 0; j < adj_deg[v]; ++j) {
                    int neighbor = adj_indices[v][j];
                    if(colored[neighbor] && c[neighbor] == chosen && neighbor != u) {
                        known = true;
                        break;
                    }
                }
                if(!known) sat[v]++;
            }
        }
        processed++;
    }
    
    min_k = 0;
    for(int x : c) min_k = max(min_k, x);
    for(int i = 0; i < N; ++i) best_sol[i] = c[i];
}

void add_to_list(int u) {
    if (!in_conflict[u]) {
        in_conflict[u] = true;
        pos_in_list[u] = conflict_list.size();
        conflict_list.push_back(u);
    }
}

void remove_from_list(int u) {
    if (in_conflict[u]) {
        in_conflict[u] = false;
        int last = conflict_list.back();
        int p = pos_in_list[u];
        conflict_list[p] = last;
        pos_in_list[last] = p;
        conflict_list.pop_back();
    }
}

// Check if we can color G_bar with k colors using Tabu Search (Min-Conflicts)
bool solve(int k) {
    // Random initialization
    for(int i = 0; i < N; ++i) color[i] = fast_rand(k) + 1;
    
    // Initialize data structures
    for(int i = 0; i < N; ++i) 
        for(int c = 1; c <= k; ++c) gamma_mat[i][c] = 0;
        
    int total_conflicts = 0;
    conflict_list.clear();
    memset(in_conflict, 0, sizeof(in_conflict));
    
    for(int u = 0; u < N; ++u) {
        for(int i = 0; i < adj_deg[u]; ++i) {
            int v = adj_indices[u][i];
            gamma_mat[u][color[v]]++;
        }
    }
    
    for(int u = 0; u < N; ++u) {
        if (gamma_mat[u][color[u]] > 0) {
            total_conflicts += gamma_mat[u][color[u]];
            add_to_list(u);
        }
    }
    // Edges are counted twice in gamma summation
    total_conflicts /= 2;
    
    memset(tabu, 0, sizeof(tabu));
    iter_cnt = 0;
    
    while (total_conflicts > 0) {
        iter_cnt++;
        // Check time every 1024 iterations
        if ((iter_cnt & 1023) == 0) {
            if ((double)clock() / CLOCKS_PER_SEC > TIME_LIMIT) return false;
        }
        
        if (conflict_list.empty()) break; // Should not happen if total_conflicts > 0
        
        // Pick a conflicting vertex
        int u = conflict_list[fast_rand(conflict_list.size())];
        
        int curr_c = color[u];
        int curr_conf = gamma_mat[u][curr_c];
        
        int best_move_c = -1;
        int best_delta = 1000000;
        
        vector<int> candidates;
        candidates.reserve(k);
        
        // Find best color to move to
        for(int c = 1; c <= k; ++c) {
            if (c == curr_c) continue;
            int delta = gamma_mat[u][c] - curr_conf;
            
            bool is_tabu = (tabu[u][c] >= iter_cnt);
            if (is_tabu) {
                // Aspiration criterion: allow tabu move if it improves global best
                // Here we strict check simply for 0 conflicts, or just valid move if desperation?
                // Standard aspiration: if total_conflicts + delta < best_found_so_far.
                // Since we want ANY valid solution, strict reduction suffices for now.
                // Or simply: if it leads to 0 conflicts, take it.
                if (total_conflicts + delta > 0) continue; 
            }
            
            if (delta < best_delta) {
                best_delta = delta;
                candidates.clear();
                candidates.push_back(c);
            } else if (delta == best_delta) {
                candidates.push_back(c);
            }
        }
        
        if (candidates.empty()) {
             // If all non-tabu moves are blocked and no aspiration met, pick random move
             int rand_c = fast_rand(k) + 1;
             while(k > 1 && rand_c == curr_c) rand_c = fast_rand(k) + 1;
             if (k == 1) rand_c = 1; 
             best_move_c = rand_c;
             best_delta = gamma_mat[u][rand_c] - curr_conf;
        } else {
             best_move_c = candidates[fast_rand(candidates.size())];
        }
        
        // Execute Move
        int new_c = best_move_c;
        if (new_c == curr_c) continue; 
        
        color[u] = new_c;
        total_conflicts += best_delta;
        
        // Update Conflict List for u
        if (gamma_mat[u][new_c] > 0) add_to_list(u);
        else remove_from_list(u);
        
        // Update Neighbors
        for(int i = 0; i < adj_deg[u]; ++i) {
            int v = adj_indices[u][i];
            gamma_mat[v][curr_c]--;
            gamma_mat[v][new_c]++;
            
            if (color[v] == curr_c) {
                // Check if v is now conflict free
                if (gamma_mat[v][curr_c] == 0) remove_from_list(v);
            }
            if (color[v] == new_c) {
                // v now has a conflict
                add_to_list(v);
            }
        }
        
        // Set Tabu
        // Dynamic tenure based on number of conflicts to balance search
        int tenure = (int)(0.6 * conflict_list.size()) + fast_rand(10);
        tabu[u][curr_c] = iter_cnt + tenure;
    }
    
    return (total_conflicts == 0);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    build_graph();
    
    // Step 1: Get initial solution
    run_dsatur();
    
    // Step 2: Optimization loop
    // Try to find a valid solution with fewer colors (cliques)
    while (min_k > 1 && (double)clock()/CLOCKS_PER_SEC < TIME_LIMIT) {
        if (solve(min_k - 1)) {
            min_k--;
            for(int i = 0; i < N; ++i) best_sol[i] = color[i];
        } else {
            // Cannot improve further within time limit
            break;
        }
    }
    
    // Output
    for(int i = 0; i < N; ++i) cout << best_sol[i] << "\n";
    
    return 0;
}
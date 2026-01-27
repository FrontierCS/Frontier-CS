#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <random>
#include <ctime>

using namespace std;

const int MAXN = 505;
int N, M;
// Adjacency matrix for the complement graph G_bar
// adj[i][j] = 1 means i and j are connected in G_bar (NOT connected in G)
bitset<MAXN> adj[MAXN]; 
// Adjacency list for G_bar for faster iteration
vector<int> adj_list[MAXN];
int degree[MAXN];

// Best solution found so far
int best_k = MAXN + 1;
int final_assignment[MAXN];

// Timer
double get_time() {
    return (double)clock() / CLOCKS_PER_SEC;
}

// Random Number Generator
mt19937 rng(1337);

// Update global best solution
void update_solution(int k, const vector<int>& assignment) {
    if (k < best_k) {
        best_k = k;
        for(int i=1; i<=N; ++i) final_assignment[i] = assignment[i];
    }
}

// --- Algorithm 1: Randomized Greedy ---
// Shuffles vertices and assigns the smallest available color sequentially.
void solve_greedy() {
    vector<int> p(N);
    for(int i=0; i<N; ++i) p[i] = i + 1;
    shuffle(p.begin(), p.end(), rng);

    vector<int> color(N + 1, 0);
    int max_c = 0;
    
    // Arrays for checking used colors efficiently
    static int used[MAXN];
    static int cookie = 0;
    
    for (int u : p) {
        cookie++; // Start a new check session for vertex u
        // Check colors of neighbors in G_bar
        for (int v : adj_list[u]) {
            if (color[v] != 0) {
                used[color[v]] = cookie;
            }
        }
        
        // Find first color not used by neighbors
        int c = 1;
        while (used[c] == cookie) c++;
        
        color[u] = c;
        if (c > max_c) max_c = c;
        
        // Pruning: if we already used more or equal colors than best solution, stop
        if (max_c >= best_k) return;
    }
    update_solution(max_c, color);
}

// --- Algorithm 2: Randomized DSATUR ---
// Dynamically picks vertex with highest saturation degree (number of different colors in neighborhood).
void solve_dsatur() {
    vector<int> color(N + 1, 0);
    vector<int> sat_deg(N + 1, 0);
    vector<int> uncolored_deg(N + 1);
    
    // Store colors used by neighbors to update sat_deg efficiently
    static bitset<MAXN> neighbor_colors[MAXN];
    for(int i=1; i<=N; ++i) {
        neighbor_colors[i].reset();
        uncolored_deg[i] = degree[i];
    }
    
    vector<bool> is_colored(N + 1, false);
    int max_c = 0;

    for (int iter = 0; iter < N; ++iter) {
        // Candidate selection
        int max_sat = -1;
        int max_deg = -1;
        vector<int> candidates;
        
        for (int i = 1; i <= N; ++i) {
            if (!is_colored[i]) {
                if (sat_deg[i] > max_sat) {
                    max_sat = sat_deg[i];
                    max_deg = uncolored_deg[i];
                    candidates.clear();
                    candidates.push_back(i);
                } else if (sat_deg[i] == max_sat) {
                    if (uncolored_deg[i] > max_deg) {
                        max_deg = uncolored_deg[i];
                        candidates.clear();
                        candidates.push_back(i);
                    } else if (uncolored_deg[i] == max_deg) {
                        candidates.push_back(i);
                    }
                }
            }
        }
        
        if (candidates.empty()) break;
        
        // Pick random candidate
        int u = candidates[rng() % candidates.size()];
        
        // Find smallest valid color
        int c = 1;
        while (neighbor_colors[u].test(c)) c++;
        
        color[u] = c;
        is_colored[u] = true;
        if (c > max_c) max_c = c;
        
        if (max_c >= best_k) return;

        // Update neighbors
        for (int v : adj_list[u]) {
            if (!is_colored[v]) {
                uncolored_deg[v]--;
                if (!neighbor_colors[v].test(c)) {
                    neighbor_colors[v].set(c);
                    sat_deg[v]++;
                }
            }
        }
    }
    update_solution(max_c, color);
}

// --- Algorithm 3: Randomized RLF (Recursive Largest First) ---
// Constructs color classes one by one by picking a maximal independent set in G_bar.
void solve_rlf() {
    bitset<MAXN> uncolored;
    for(int i=1; i<=N; ++i) uncolored.set(i);
    
    vector<int> color(N + 1, 0);
    int current_c = 0;
    int colored_cnt = 0;

    while (colored_cnt < N) {
        current_c++;
        if (current_c >= best_k) return;
        
        // Candidates for the current color class
        bitset<MAXN> candidates = uncolored;
        
        // Step 1: Pick first vertex of the class
        // Heuristic: Vertex in candidates with max neighbors in uncolored
        int max_d = -1;
        vector<int> bests;
        
        for (int i = 1; i <= N; ++i) {
            if (candidates.test(i)) {
                // Count neighbors in uncolored set
                int d = (adj[i] & uncolored).count();
                if (d > max_d) {
                    max_d = d;
                    bests.clear();
                    bests.push_back(i);
                } else if (d == max_d) {
                    bests.push_back(i);
                }
            }
        }
        
        if (bests.empty()) break;
        int u = bests[rng() % bests.size()];
        
        color[u] = current_c;
        uncolored.reset(u);
        candidates.reset(u); // Cannot add u again
        colored_cnt++;
        
        // Only vertices NOT connected to u in G_bar can be in the same color class
        // In G_bar, non-neighbors of u are valid. Neighbors are INVALID.
        // Wait: Color class in G_bar is Independent Set.
        // So we cannot have edges between nodes in same class.
        // So candidates must restrict to NON-neighbors of u.
        // adj[u] contains neighbors. We want NOT neighbors.
        candidates &= ~adj[u];
        
        // Step 2: Add more vertices to current class
        while (candidates.count() > 0) {
            // Heuristic: Pick v in candidates with max neighbors in uncolored
            max_d = -1;
            bests.clear();
            
            for (int v = 1; v <= N; ++v) {
                if (candidates.test(v)) {
                    int d = (adj[v] & uncolored).count();
                    if (d > max_d) {
                        max_d = d;
                        bests.clear();
                        bests.push_back(v);
                    } else if (d == max_d) {
                        bests.push_back(v);
                    }
                }
            }
            
            if (bests.empty()) break;
            int v = bests[rng() % bests.size()];
            
            color[v] = current_c;
            uncolored.reset(v);
            candidates.reset(v); // remove self
            colored_cnt++;
            
            // Filter candidates: remove neighbors of v
            candidates &= ~adj[v];
        }
    }
    update_solution(current_c, color);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    // Initialize adj for G_bar as complete graph minus self-loops
    for(int i=1; i<=N; ++i) {
        for(int j=1; j<=N; ++j) {
            if (i != j) adj[i].set(j);
        }
    }
    
    // Read edges of G. An edge in G means NO edge in G_bar.
    for(int i=0; i<M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].reset(v);
        adj[v].reset(u);
    }
    
    // Build adj_list and degree for G_bar
    for(int i=1; i<=N; ++i) {
        for(int j=1; j<=N; ++j) {
            if (adj[i].test(j)) {
                adj_list[i].push_back(j);
            }
        }
        degree[i] = adj_list[i].size();
    }
    
    // Initial dummy solution
    vector<int> initial(N+1);
    for(int i=1; i<=N; ++i) initial[i] = i;
    update_solution(N, initial);
    
    // Main optimization loop
    int iter = 0;
    // Time limit 2.0s, leave some buffer
    while (get_time() < 1.95) {
        iter++;
        // Interleave different strategies
        if (iter % 8 == 0) {
             solve_rlf();     // High quality, slightly slower
        } else if (iter % 3 == 0) {
             solve_dsatur();  // Good balance
        } else {
             solve_greedy();  // Fast exploration
        }
    }
    
    // Output result
    for(int i=1; i<=N; ++i) {
        cout << final_assignment[i] << "\n";
    }
    
    return 0;
}
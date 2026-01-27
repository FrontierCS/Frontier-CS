#include <iostream>
#include <vector>
#include <algorithm>
#include <bitset>
#include <ctime>
#include <cstdlib>
#include <random>
#include <numeric>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 505;

int N, M;
// adj[i] contains 1 at bit j if i and j are adjacent in the COMPLEMENT graph 
// (i.e., they DO NOT share an edge in G and thus cannot have the same clique ID).
bitset<MAXN> adj[MAXN]; 

// Global best solution tracking
int best_k = 1000;
vector<int> best_ids;

// Helper to check elapsed time
double get_time() {
    return (double)clock() / CLOCKS_PER_SEC;
}

// Random number generator
mt19937 rng(1337);

// Greedy coloring with a specific permutation
void solve_greedy(const vector<int>& p) {
    vector<int> ids(N + 1, 0);
    int current_max = 0;
    
    for (int u : p) {
        bitset<MAXN> used;
        for (int v = 1; v <= N; ++v) {
            // If u and v conflict (adjacent in complement) and v is colored
            if (adj[u].test(v) && ids[v] != 0) {
                used.set(ids[v]);
            }
        }
        
        // Find first unused color
        int c = 1;
        while (used.test(c)) c++;
        ids[u] = c;
        if (c > current_max) current_max = c;
        
        // Pruning: if we already used as many colors as the best known solution, stop
        if (current_max >= best_k) return; 
    }
    
    if (current_max < best_k) {
        best_k = current_max;
        best_ids = ids;
    }
}

// DSatur Algorithm
void solve_dsatur() {
    vector<int> ids(N + 1, 0);
    vector<int> sat_degree(N + 1, 0);
    vector<int> degree(N + 1, 0);
    vector<bitset<MAXN>> adj_colors(N + 1); // Tracks colors used by neighbors in complement graph
    
    for (int i = 1; i <= N; ++i) {
        degree[i] = adj[i].count();
    }
    
    int uncolored_count = N;
    int current_max = 0;
    
    while (uncolored_count > 0) {
        // Select vertex with max saturation degree
        int best_u = -1;
        int max_sat = -1;
        int max_deg = -1;
        
        vector<int> candidates;
        
        for (int i = 1; i <= N; ++i) {
            if (ids[i] == 0) {
                if (sat_degree[i] > max_sat) {
                    max_sat = sat_degree[i];
                    max_deg = degree[i];
                    candidates.clear();
                    candidates.push_back(i);
                } else if (sat_degree[i] == max_sat) {
                    if (degree[i] > max_deg) {
                        max_deg = degree[i];
                        candidates.clear();
                        candidates.push_back(i);
                    } else if (degree[i] == max_deg) {
                        candidates.push_back(i);
                    }
                }
            }
        }
        
        // Random tie-breaking
        int idx = 0;
        if (candidates.size() > 1) {
            idx = uniform_int_distribution<int>(0, candidates.size() - 1)(rng);
        }
        best_u = candidates[idx];
        
        // Assign smallest legal color
        int c = 1;
        while (adj_colors[best_u].test(c)) c++;
        
        ids[best_u] = c;
        if (c > current_max) current_max = c;
        if (current_max >= best_k) return;
        
        uncolored_count--;
        
        // Update neighbors
        for (int v = 1; v <= N; ++v) {
            if (ids[v] == 0 && adj[best_u].test(v)) {
                if (!adj_colors[v].test(c)) {
                    adj_colors[v].set(c);
                    sat_degree[v]++;
                }
            }
        }
    }
    
    if (current_max < best_k) {
        best_k = current_max;
        best_ids = ids;
    }
}

// Recursive Largest First (RLF) Algorithm
void solve_rlf() {
    vector<int> ids(N + 1, 0);
    bitset<MAXN> uncolored;
    for (int i = 1; i <= N; ++i) uncolored.set(i);
    
    int current_k = 0;
    int uncolored_cnt = N;
    
    while (uncolored_cnt > 0) {
        current_k++;
        if (current_k >= best_k) return;
        
        // Start new color class with vertex having max degree in uncolored subgraph
        int best_u = -1;
        int max_deg = -1;
        vector<int> candidates_vec;
        
        for (int i = 1; i <= N; ++i) {
            if (uncolored.test(i)) {
                int d = (adj[i] & uncolored).count();
                if (d > max_deg) {
                    max_deg = d;
                    candidates_vec.clear();
                    candidates_vec.push_back(i);
                } else if (d == max_deg) {
                    candidates_vec.push_back(i);
                }
            }
        }
        
        if (candidates_vec.empty()) break; 
        
        int idx = 0;
        if (candidates_vec.size() > 1) {
             idx = uniform_int_distribution<int>(0, candidates_vec.size() - 1)(rng);
        }
        best_u = candidates_vec[idx];
        
        ids[best_u] = current_k;
        uncolored.reset(best_u);
        uncolored_cnt--;
        
        // Vertices compatible with current color class so far
        // Must be uncolored AND NOT adjacent to best_u (in complement)
        bitset<MAXN> candidates = uncolored & (~adj[best_u]);
        // Vertices incompatible (adjacent in complement)
        bitset<MAXN> non_candidates = uncolored & adj[best_u];
        
        // Greedily add more vertices to this class
        while (candidates.any()) {
            // Heuristic: pick vertex in candidates that maximizes neighbors in non_candidates
            // This leaves "harder" vertices for later or clears constraints
            int best_v = -1;
            int max_common = -1;
            vector<int> v_candidates;
            
            for (int v = 1; v <= N; ++v) {
                if (candidates.test(v)) {
                    int common = (adj[v] & non_candidates).count();
                    if (common > max_common) {
                        max_common = common;
                        v_candidates.clear();
                        v_candidates.push_back(v);
                    } else if (common == max_common) {
                        v_candidates.push_back(v);
                    }
                }
            }
            
            if (v_candidates.empty()) break;
            
            idx = 0;
            if (v_candidates.size() > 1) {
                idx = uniform_int_distribution<int>(0, v_candidates.size() - 1)(rng);
            }
            best_v = v_candidates[idx];
            
            ids[best_v] = current_k;
            uncolored.reset(best_v);
            uncolored_cnt--;
            
            // Vertices in candidates that conflict with new member best_v must be removed
            bitset<MAXN> newly_blocked = candidates & adj[best_v];
            
            candidates.reset(best_v);
            candidates ^= newly_blocked; // Remove newly blocked
            non_candidates |= newly_blocked; // Add them to non_candidates
        }
    }
    
    if (current_k < best_k) {
        best_k = current_k;
        best_ids = ids;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> N >> M)) return 0;
    
    // Initialize adjacency matrix for Complement Graph
    // Start with all possible edges (complete graph)
    for(int i=1; i<=N; ++i) {
        adj[i].set(); 
        adj[i].reset(i); // No self loops
        for(int k=N+1; k<MAXN; ++k) adj[i].reset(k); // Clear out of bounds
        adj[i].reset(0);
    }
    
    // Read edges of G. If edge {u, v} exists in G, remove it from Complement Graph.
    for(int i=0; i<M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].reset(v);
        adj[v].reset(u);
    }
    
    // Default valid solution: each vertex is its own clique
    best_k = N;
    best_ids.resize(N + 1);
    iota(best_ids.begin(), best_ids.end(), 0); 
    
    // 1. Run RLF (Recursive Largest First) - usually very effective
    solve_rlf();
    
    // 2. Run DSatur
    solve_dsatur();
    
    // 3. Run Greedy with sorted by degree (Largest Degree First)
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    sort(p.begin(), p.end(), [&](int a, int b){
        return adj[a].count() > adj[b].count();
    });
    solve_greedy(p);
    
    // Iterative improvement until time limit
    // Cycle through RLF, DSatur, and Random Greedy
    int iter = 0;
    while (get_time() < 1.95) {
        iter++;
        if (iter % 5 == 0) {
             solve_dsatur();
        } else if (iter % 5 == 1) {
             solve_rlf();
        } else {
             shuffle(p.begin(), p.end(), rng);
             solve_greedy(p);
        }
    }
    
    // Output result
    for(int i=1; i<=N; ++i) {
        cout << best_ids[i] << "\n";
    }
    
    return 0;
}
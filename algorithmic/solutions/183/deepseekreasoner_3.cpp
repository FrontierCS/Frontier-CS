#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>

// Optimization pragmas
#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

using namespace std;

// Globals
int N, M;
vector<vector<int>> adj;
vector<char> adj_mat; // Flattened N*N adjacency matrix for O(1) checks
vector<int> degree;

// Best solution found
vector<int> best_sol;
int best_k = -1;

// Time management
auto start_time = chrono::high_resolution_clock::now();
const double TIME_LIMIT = 1.90; // seconds

// Check if time limit is approaching
inline bool check_time() {
    auto current_time = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = current_time - start_time;
    return diff.count() < TIME_LIMIT;
}

// Check edge existence: O(1)
inline bool has_edge(int u, int v) {
    if (u > v) swap(u, v);
    return adj_mat[u * N + v];
}

void solve() {
    // Vectors reused across iterations to minimize allocation
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);
    
    vector<int> current_sol;      // Indices of vertices in current IS
    vector<int> in_set(N, 0);     // Boolean flag for current IS
    vector<char> blocked(N, 0);   // Used in greedy phase
    vector<int> neighbor_count(N, 0); // Count of neighbors in S (for local search)
    vector<vector<int>> candidates(N); // Local search candidates
    
    // Random engine
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    
    // Auxiliary vector for sorting
    vector<int> weights(N);

    // Initial simple greedy run might have happened implicitly, but we loop
    int iter = 0;
    while (check_time()) {
        iter++;
        
        // --- 1. Randomized Greedy Construction ---
        
        // Randomize vertex ordering
        // Probabilistic strategy: Prefer low degree vertices, but add noise
        if (iter % 10 == 0) {
            // Pure random shuffle occasionally to escape local basins
            shuffle(p.begin(), p.end(), rng);
        } else {
            // Biased sort
            for(int i=0; i<N; ++i) {
                // Weight = Degree * Scaling + Random Noise
                // Lower weight -> processed earlier -> more likely to be in set
                weights[i] = degree[i] * 20 + (rng() % 500);
            }
            sort(p.begin(), p.end(), [&](int a, int b){
                return weights[a] < weights[b];
            });
        }
        
        // Build maximal independent set
        current_sol.clear();
        fill(in_set.begin(), in_set.end(), 0);
        fill(blocked.begin(), blocked.end(), 0);
        
        for (int u : p) {
            if (!blocked[u]) {
                in_set[u] = 1;
                current_sol.push_back(u);
                blocked[u] = 1; // Block self
                for (int v : adj[u]) {
                    blocked[v] = 1; // Block neighbors
                }
            }
        }
        
        // --- 2. Local Search Improvement ---
        // Try (1, 2)-swaps: Remove 1 vertex, add 2 vertices
        // This is a hill-climbing step
        
        bool improved = true;
        while (improved && check_time()) {
            improved = false;
            
            // Recompute neighbor counts relative to current S
            fill(neighbor_count.begin(), neighbor_count.end(), 0);
            for (int u : current_sol) {
                for (int v : adj[u]) {
                    neighbor_count[v]++;
                }
            }
            
            // Prepare candidates
            // Clear previous candidates
            for(int u : current_sol) candidates[u].clear();
            
            // Identify vertices outside S that have exactly 1 neighbor in S
            for (int v = 0; v < N; ++v) {
                if (in_set[v]) continue; 
                
                if (neighbor_count[v] == 1) {
                    // Find the single neighbor u in S
                    for (int u : adj[v]) {
                        if (in_set[u]) {
                            candidates[u].push_back(v);
                            break; 
                        }
                    }
                } else if (neighbor_count[v] == 0) {
                    // (0, 1) Improvement: Simply add v
                    // This creates a larger set immediately
                    in_set[v] = 1;
                    current_sol.push_back(v);
                    improved = true;
                    // Restart loop to consistent state
                    goto end_scan;
                }
            }
            
            // Try (1, 2) swap
            // For each u in S, check if we can replace u with {v1, v2} from candidates[u]
            for (int u : current_sol) {
                const auto& cands = candidates[u];
                if (cands.size() >= 2) {
                    // Check pairs in candidates
                    for (size_t i = 0; i < cands.size(); ++i) {
                        for (size_t j = i + 1; j < cands.size(); ++j) {
                            int v1 = cands[i];
                            int v2 = cands[j];
                            // If v1 and v2 are not connected
                            if (!has_edge(v1, v2)) {
                                // Execute Swap
                                in_set[u] = 0;
                                in_set[v1] = 1;
                                in_set[v2] = 1;
                                improved = true;
                                goto end_scan;
                            }
                        }
                    }
                }
            }
            
            end_scan:;
            // If improved, we need to refresh current_sol vector for next pass
            if (improved) {
                current_sol.clear();
                for(int i = 0; i < N; ++i) {
                    if (in_set[i]) current_sol.push_back(i);
                }
            }
        }
        
        // Update global best
        if ((int)current_sol.size() > best_k) {
            best_k = current_sol.size();
            best_sol = in_set;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    // Read Input
    if (!(cin >> N >> M)) return 0;
    
    adj.resize(N);
    degree.resize(N, 0);
    adj_mat.assign(N * N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert to 0-based
        if (u < 0 || v < 0 || u >= N || v >= N || u == v) continue;
        
        adj[u].push_back(v);
        adj[v].push_back(u);
        
        // Populate adjacency matrix (triangular or full, doing triangular u<v logic for access)
        if (u > v) swap(u, v);
        adj_mat[u * N + v] = 1;
        
        degree[u]++;
        degree[v]++;
    }
    
    // Clean adjacency lists (remove duplicates)
    for(int i=0; i<N; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
        // Update degree count to reflect unique neighbors (optional but better heuristic)
        degree[i] = adj[i].size(); 
    }
    
    // Init best solution
    best_sol.assign(N, 0);
    best_k = 0;
    
    solve();
    
    // Output result
    for (int i = 0; i < N; ++i) {
        cout << best_sol[i] << "\n";
    }
    
    return 0;
}
#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>
#include <numeric>

using namespace std;

// ----------------------
// Global Constants
// ----------------------
const int MAXN = 1005;

// ----------------------
// Global Variables
// ----------------------
int N, M;
vector<int> adj[MAXN];
bool adj_mat[MAXN][MAXN];
int initial_degree[MAXN];

// To store the best solution found
struct Solution {
    vector<int> s;      // Vertices in the independent set
    bool is_in[MAXN];   // Direct lookup
    int count;          // Size of set

    Solution() : count(0) {
        memset(is_in, 0, sizeof(is_in));
    }
    
    void add(int v) {
        if (!is_in[v]) {
            is_in[v] = true;
            s.push_back(v);
            count++;
        }
    }

    void clear() {
        s.clear();
        memset(is_in, 0, sizeof(is_in));
        count = 0;
    }
} best_sol;

// Random Number Generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Time Management
auto start_time = chrono::high_resolution_clock::now();
// Setting slightly below 2.0s to be safe
const double TIME_LIMIT = 1.95; 

double get_elapsed_time() {
    auto now = chrono::high_resolution_clock::now();
    chrono::duration<double> diff = now - start_time;
    return diff.count();
}

// ----------------------
// Helper Functions
// ----------------------
inline bool are_connected(int u, int v) {
    return adj_mat[u][v];
}

// ----------------------
// Core Logic
// ----------------------

void solve() {
    // Arrays reused per iteration to avoid allocation overhead
    static bool eligible[MAXN];
    static int current_degree[MAXN];
    static vector<int> candidates;
    static vector<int> best_candidates;
    static vector<int> to_remove;
    static Solution current_sol;
    
    // Reserve capacity
    if (candidates.capacity() < (size_t)N + 1) candidates.reserve(N + 1);
    if (best_candidates.capacity() < (size_t)N + 1) best_candidates.reserve(N + 1);
    if (to_remove.capacity() < (size_t)N + 1) to_remove.reserve(N + 1);

    // Main loop
    while (get_elapsed_time() < TIME_LIMIT) {
        // --- 1. Randomized Greedy Construction ---
        
        // Reset state
        current_sol.clear();
        for (int i = 1; i <= N; ++i) {
            eligible[i] = true;
            current_degree[i] = initial_degree[i];
        }
        
        candidates.clear();
        for (int i = 1; i <= N; ++i) candidates.push_back(i);
        
        int remaining_cnt = N;

        while (remaining_cnt > 0) {
            int min_deg = 1e9;
            best_candidates.clear();

            // Find min degree candidates among eligible vertices
            for (int v : candidates) {
                if (!eligible[v]) continue;
                if (current_degree[v] < min_deg) {
                    min_deg = current_degree[v];
                    best_candidates.clear();
                    best_candidates.push_back(v);
                } else if (current_degree[v] == min_deg) {
                    best_candidates.push_back(v);
                }
            }
            
            if (best_candidates.empty()) break; 

            // Pick one randomly from the best candidates
            int idx = uniform_int_distribution<int>(0, best_candidates.size() - 1)(rng);
            int v = best_candidates[idx];

            // Add to solution
            current_sol.add(v);

            // Determine vertices to remove (v and its neighbors)
            to_remove.clear();
            to_remove.push_back(v);
            for (int neighbor : adj[v]) {
                if (eligible[neighbor]) {
                    to_remove.push_back(neighbor);
                }
            }

            // Remove vertices and update degrees dynamically
            for (int r : to_remove) {
                if (eligible[r]) {
                    eligible[r] = false;
                    remaining_cnt--;
                    // Since r is removed, neighbors of r have their degree reduced
                    for (int neighbor : adj[r]) {
                        if (eligible[neighbor]) {
                            current_degree[neighbor]--;
                        }
                    }
                }
            }
        }
        
        // Update global best if better found immediately
        if (current_sol.count > best_sol.count) {
            best_sol = current_sol;
        }

        // --- 2. Local Search Improvement ---
        // Try (1, 2) swaps: Remove 1 vertex from S, add 2 vertices to S.
        
        bool improved = true;
        while (improved && get_elapsed_time() < TIME_LIMIT) {
            improved = false;
            
            static int blocker_count[MAXN];
            static int blocker_id[MAXN]; // Stores the vertex in S that blocks u (valid if count==1)
            
            // Identify vertices NOT in S
            vector<int> not_in_S;
            not_in_S.reserve(N);
            for(int i = 1; i <= N; ++i) {
                if(!current_sol.is_in[i]) {
                    not_in_S.push_back(i);
                    blocker_count[i] = 0;
                }
            }

            // Compute blockers for vertices not in S
            for(int u : not_in_S) {
                for(int neighbor : adj[u]) {
                    if(current_sol.is_in[neighbor]) {
                        blocker_count[u]++;
                        if(blocker_count[u] == 1) blocker_id[u] = neighbor;
                        else if(blocker_count[u] > 1) break; // Optimization
                    }
                }
            }

            // Try to swap out each vertex v in S
            // We use a copy of the current set to iterate safely
            vector<int> current_S_vec = current_sol.s;
            
            for(int v : current_S_vec) {
                // Find potential replacements: u not in S blocked ONLY by v
                vector<int> replacements;
                replacements.reserve(N);
                for(int u : not_in_S) {
                    if(blocker_count[u] == 1 && blocker_id[u] == v) {
                        replacements.push_back(u);
                    }
                }

                // If we have at least 2 potential replacements, check if any pair is independent
                if(replacements.size() >= 2) {
                    int r1 = -1, r2 = -1;
                    // Check all pairs in replacements
                    for(size_t i = 0; i < replacements.size(); ++i) {
                        for(size_t j = i + 1; j < replacements.size(); ++j) {
                            if(!are_connected(replacements[i], replacements[j])) {
                                r1 = replacements[i];
                                r2 = replacements[j];
                                goto found_improvement;
                            }
                        }
                    }
                    
                    found_improvement:
                    if(r1 != -1) {
                        // Apply Swap: Remove v, Add r1 and r2
                        
                        // Remove v
                        current_sol.is_in[v] = false;
                        for(size_t k=0; k<current_sol.s.size(); ++k) {
                            if(current_sol.s[k] == v) {
                                current_sol.s[k] = current_sol.s.back();
                                current_sol.s.pop_back();
                                break;
                            }
                        }
                        current_sol.count--;

                        // Add r1
                        current_sol.add(r1);
                        // Add r2
                        current_sol.add(r2);
                        
                        improved = true;
                        break; // Restart local search loop to recompute blockers
                    }
                }
            }
        }

        if (current_sol.count > best_sol.count) {
            best_sol = current_sol;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    memset(adj_mat, 0, sizeof(adj_mat));
    memset(initial_degree, 0, sizeof(initial_degree));

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v && !adj_mat[u][v]) {
            adj[u].push_back(v);
            adj[v].push_back(u);
            adj_mat[u][v] = true;
            adj_mat[v][u] = true;
            initial_degree[u]++;
            initial_degree[v]++;
        }
    }

    solve();

    // Fallback if no solution found (should not happen)
    if (best_sol.count == 0) {
        vector<bool> used(N + 1, false);
        for(int i = 1; i <= N; ++i) {
            if(!used[i]) {
                cout << 1 << "\n";
                used[i] = true;
                for(int v : adj[i]) used[v] = true;
            } else {
                cout << 0 << "\n";
            }
        }
    } else {
        for (int i = 1; i <= N; ++i) {
            cout << (best_sol.is_in[i] ? 1 : 0) << "\n";
        }
    }

    return 0;
}
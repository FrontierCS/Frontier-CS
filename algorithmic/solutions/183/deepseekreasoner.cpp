#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>
#include <ctime>

using namespace std;

// Constants and Globals
const int MAXN = 10005;
int N, M;
vector<int> adj[MAXN];
int degree[MAXN];

// Timer Logic
double start_time;
double get_time() {
    return (double)(clock() - start_time) / CLOCKS_PER_SEC;
}

// Random Number Generator
mt19937 rng(1337);

// Solution Structure
struct Solution {
    vector<bool> in_set;
    int k; // Size of Independent Set
    Solution() : in_set(MAXN, false), k(0) {}
};

Solution best_sol;

// Preprocessing Input
void read_input() {
    if (!(cin >> N >> M)) return;
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    for (int i = 1; i <= N; ++i) {
        degree[i] = adj[i].size();
    }
}

// Helper: Check adjacency efficiently
// Since N <= 10000, adjacency matrix is too large (maybe), but linear scan on adj list is fast for sparse graphs.
bool are_adjacent(int u, int v) {
    if (adj[u].size() > adj[v].size()) swap(u, v);
    for (int x : adj[u]) {
        if (x == v) return true;
    }
    return false;
}

// Randomized Greedy Algorithm
// Prioritizes low-degree nodes with random noise to explore state space.
Solution randomized_greedy() {
    Solution sol;
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);

    // Calculate weights: strict low degree + randomness
    vector<pair<int, int>> weights(N);
    for(int i = 0; i < N; ++i) {
        int u = p[i];
        // weight = degree * FACTOR + random
        // Lower weight is processed first.
        weights[i] = { degree[u] * 25 + (int)(rng() % 500), u };
    }
    sort(weights.begin(), weights.end());

    vector<bool> blocked(N + 1, false);
    for (int i = 0; i < N; ++i) {
        int u = weights[i].second;
        if (!blocked[u]) {
            sol.in_set[u] = true;
            sol.k++;
            blocked[u] = true;
            for (int v : adj[u]) {
                blocked[v] = true;
            }
        }
    }
    return sol;
}

// Local Search: (1, 2) Exchange
// Tries to remove 1 vertex from S and add 2 vertices from V \ S.
// Maintains a conflict array for efficiency.
void local_search(Solution& sol) {
    // Collect current set explicitly for iteration
    vector<int> S;
    S.reserve(N);
    for (int i = 1; i <= N; ++i) {
        if (sol.in_set[i]) S.push_back(i);
    }

    // Compute conflicts: conflict[u] = number of neighbors of u that are in S
    vector<int> conflict(N + 1, 0);
    for (int u = 1; u <= N; ++u) {
        if (!sol.in_set[u]) {
            int c = 0;
            for (int v : adj[u]) {
                if (sol.in_set[v]) c++;
            }
            conflict[u] = c;
        }
    }

    bool improved = true;
    // Repeat until local optimum
    while (improved) {
        improved = false;
        // Shuffle S to randomize removal order
        shuffle(S.begin(), S.end(), rng);
        
        for (int idx = 0; idx < (int)S.size(); ++idx) {
            int u = S[idx];
            // Identify candidates: neighbors of u that are NOT in S and have conflict == 1 (only u)
            // If u is removed, their conflict drops to 0, becoming valid candidates.
            vector<int> candidates;
            candidates.reserve(degree[u]);
            
            for (int v : adj[u]) {
                // v is definitely not in S (adj to u in S).
                if (conflict[v] == 1) {
                    candidates.push_back(v);
                }
            }

            if (candidates.size() >= 2) {
                // Search for a pair {c1, c2} in candidates that are NOT adjacent
                int c1 = -1, c2 = -1;
                bool found = false;
                
                // Heuristic check limit to avoid O(deg^2) in dense clusters
                int checks = 0;
                int max_checks = 100;
                
                for (size_t i = 0; i < candidates.size() && !found; ++i) {
                    for (size_t j = i + 1; j < candidates.size(); ++j) {
                        if (!are_adjacent(candidates[i], candidates[j])) {
                            c1 = candidates[i];
                            c2 = candidates[j];
                            found = true;
                            break;
                        }
                        checks++;
                        if (checks > max_checks) break;
                    }
                    if (checks > max_checks) break;
                }

                if (found) {
                    // Update Set: Remove u, Add c1, Add c2
                    
                    // 1. Remove u
                    sol.in_set[u] = false;
                    sol.k--;
                    conflict[u] = 0; // Reset conflict for u (it is now outside, will be recalculated implicitly by delta or starts at 0 neighbors in S_new minus {c1,c2})
                    // Neighbors of u currently outside S have their conflict decreased
                    for (int v : adj[u]) {
                        if (!sol.in_set[v]) conflict[v]--;
                    }
                    
                    // 2. Add c1
                    sol.in_set[c1] = true;
                    sol.k++;
                    // Neighbors of c1 currently outside S have their conflict increased
                    for (int v : adj[c1]) {
                        if (!sol.in_set[v]) conflict[v]++;
                    }
                    
                    // 3. Add c2
                    sol.in_set[c2] = true;
                    sol.k++;
                    // Neighbors of c2 currently outside S have their conflict increased
                    for (int v : adj[c2]) {
                        if (!sol.in_set[v]) conflict[v]++;
                    }
                    
                    // Update S vector for valid state in next iterations
                    S[idx] = c1;
                    S.push_back(c2);
                    
                    improved = true;
                    // Break to restart logical sweep or just continue? Breaking ensures clean state (S shuffled again at top)
                    break; 
                }
            }
        }
    }
}

int main() {
    start_time = clock();
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Seed RNG
    rng.seed(chrono::high_resolution_clock::now().time_since_epoch().count());

    read_input();
    
    best_sol.k = -1;
    
    // Time constrained loop
    // 2.0s limit, stop at 1.95s to be safe
    while (get_time() < 1.95) {
        Solution curr = randomized_greedy();
        local_search(curr);
        
        if (curr.k > best_sol.k) {
            best_sol = curr;
        }
    }
    
    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << (best_sol.in_set[i] ? 1 : 0) << "\n";
    }
    
    return 0;
}
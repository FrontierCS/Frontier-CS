#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <cstring>
#include <numeric>

using namespace std;

// Globals used for the graph and solution state
int N, M;
vector<int> adj[1005];

// Stores the best independent set found so far
vector<int> best_sol;
int best_k = -1;

// Stores the current working solution during an iteration
bool in_set[1005];
// helper array: counts how many neighbors of vertex i are currently in the set S
int neighbor_in_set_cnt[1005];

// Random number generator seeded with time
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Adds vertex u to the current set S
void add_node(int u, int& current_k) {
    if (in_set[u]) return;
    in_set[u] = true;
    current_k++;
    for (int v : adj[u]) {
        neighbor_in_set_cnt[v]++;
    }
}

// Removes vertex u from the current set S
void remove_node(int u, int& current_k) {
    if (!in_set[u]) return;
    in_set[u] = false;
    current_k--;
    for (int v : adj[u]) {
        neighbor_in_set_cnt[v]--;
    }
}

void solve() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Identify and remove duplicate edges to ensure neighbor counts are accurate.
    // The problem statement says multiple edges imply the same constraint.
    for (int i = 1; i <= N; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    // Vector p used for iterating vertices in random orders
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);

    // Initialize best solution found
    best_k = 0;
    best_sol.assign(N + 1, 0);

    auto start_time = chrono::high_resolution_clock::now();
    // Time limit is 2.0s, we stop a bit earlier to ensure output is printed
    double time_limit = 1.95;

    // Buffer for swap candidates
    vector<int> candidates_1;
    candidates_1.reserve(N);

    // Main optimization loop: Randomized Greedy with Local Search (Restarts)
    while (true) {
        // Check time limit
        auto curr_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > time_limit) break;

        // Reset current solution
        memset(in_set, 0, sizeof(bool) * (N + 1));
        memset(neighbor_in_set_cnt, 0, sizeof(int) * (N + 1));
        int current_k = 0;

        // 1. Randomized Maximal Independent Set construction
        shuffle(p.begin(), p.end(), rng);
        for (int x : p) {
            // A vertex is a candidate if none of its neighbors are in S
            if (neighbor_in_set_cnt[x] == 0) {
                add_node(x, current_k);
            }
        }

        // 2. Local Search (Hill Climbing / Plateau Search)
        // We try to improve the solution by swapping vertices.
        // Specifically, (1, 2)-swaps are size-increasing moves where we remove 1 and add 2.
        // We approximate this by performing (1, 1)-swaps (plateau moves) and checking if
        // new vertices become available to add.
        
        int no_improve_iter = 0;
        int max_no_improve = N; // Stop local search if stuck for N iterations

        while (no_improve_iter < max_no_improve) {
            // Step A: "Fill Up" - Add any valid nodes immediately
            // This captures cases where a previous swap freed up a node (or multiple)
            bool added_any = false;
            
            // Random start point in p to avoid bias
            int offset = rng() % N;
            for (int i = 0; i < N; ++i) {
                int u = p[(i + offset) % N];
                if (!in_set[u] && neighbor_in_set_cnt[u] == 0) {
                    add_node(u, current_k);
                    added_any = true;
                    // Reset stall counter since we improved (or at least changed structure beneficially)
                    no_improve_iter = 0; 
                }
            }
            
            // If we managed to increase size, just loop again to try filling more
            if (added_any) continue;

            // Step B: "Plateau Swap"
            // Look for vertices v NOT in S that have exactly 1 neighbor in S.
            // Swapping v in and its neighbor u out maintains size K.
            candidates_1.clear();
            for (int i = 1; i <= N; ++i) {
                if (!in_set[i] && neighbor_in_set_cnt[i] == 1) {
                    candidates_1.push_back(i);
                }
            }

            // If no such candidates, we are in a deep local optimum (or simple optimum)
            if (candidates_1.empty()) break;

            // Pick a random candidate for the swap
            int v = candidates_1[rng() % candidates_1.size()];

            // Find the unique neighbor u in S
            int u = -1;
            for (int neighbor : adj[v]) {
                if (in_set[neighbor]) {
                    u = neighbor;
                    break;
                }
            }
            
            // Perform the swap: remove u, add v
            remove_node(u, current_k);
            add_node(v, current_k);

            // Increment stalling counter. Note that if this swap unlocks another vertex w,
            // it will be caught in Step A of the next iteration.
            no_improve_iter++;
        }

        // Update global best if we found a larger set
        if (current_k > best_k) {
            best_k = current_k;
            for (int i = 1; i <= N; ++i) {
                best_sol[i] = in_set[i] ? 1 : 0;
            }
        }
    }

    // Output the best solution found
    for (int i = 1; i <= N; ++i) {
        cout << best_sol[i] << "\n";
    }
}

int main() {
    solve();
    return 0;
}
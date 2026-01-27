#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <ctime>
#include <cstdlib>

using namespace std;

// Time limit safe margin (Time Limit is 2.0s)
const double TIME_LIMIT = 1.95;

int N, M;
vector<vector<int>> adj;
vector<int> best_solution;
int min_k;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    adj.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u != v) {
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
    }

    // Preprocessing: simplify graph (remove duplicates)
    // This helps in correctly calculating degrees in a simple graph context.
    for (int i = 1; i <= N; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    // Initialize best solution with a safe fallback (all vertices selected)
    min_k = N + 1;
    best_solution.assign(N + 1, 1);

    // Working arrays to avoid reallocation in loop
    vector<int> curr_deg(N + 1);
    vector<int> current_sol(N + 1);
    vector<int> prune_order(N);
    iota(prune_order.begin(), prune_order.end(), 1);

    clock_t start_time = clock();
    srand((unsigned int)(time(NULL) + clock()));

    int iter = 0;
    while (true) {
        // Check time limit
        if (double(clock() - start_time) / CLOCKS_PER_SEC > TIME_LIMIT) break;
        iter++;

        // 1. Initialization for this iteration
        long long rem_edges_count = 0;
        for (int i = 1; i <= N; ++i) {
            curr_deg[i] = (int)adj[i].size();
            current_sol[i] = 0;
            rem_edges_count += curr_deg[i];
        }
        rem_edges_count /= 2;

        int current_k = 0;

        // 2. Construction (Randomized Greedy)
        // Heuristic: Dynamic Max Degree
        while (rem_edges_count > 0) {
            int best_v = -1;

            if (iter == 1) {
                // First run: Deterministic Greedy (Strict Max Degree)
                int max_d = -1;
                for (int i = 1; i <= N; ++i) {
                    if (!current_sol[i] && curr_deg[i] > max_d) {
                        max_d = curr_deg[i];
                        best_v = i;
                    }
                }
            } else {
                // Subsequent runs: Randomized Greedy
                // Add noise to degrees to explore different solutions
                double max_score = -1e18;
                
                // We iterate all vertices. N=10000 is small enough for this loop 
                // to run many times within 2 seconds.
                for (int i = 1; i <= N; ++i) {
                    if (current_sol[i]) continue;
                    if (curr_deg[i] == 0) continue;
                    
                    // Score = current_degree + noise
                    // The noise allows picking suboptimal local moves to escape local optima
                    double noise = (double)rand() / RAND_MAX;
                    double score = curr_deg[i] + noise * 10.0; 
                    
                    if (score > max_score) {
                        max_score = score;
                        best_v = i;
                    }
                }
                
                // Fallback (should not be reached if rem_edges_count > 0)
                if (best_v == -1) {
                    for (int i = 1; i <= N; ++i) {
                        if (!current_sol[i] && curr_deg[i] > 0) {
                            best_v = i; break;
                        }
                    }
                }
            }

            if (best_v == -1) break; 

            // Add chosen vertex to cover
            current_sol[best_v] = 1;
            current_k++;

            // Update degrees of neighbors
            // If we add u to S, edge (u, v) is covered.
            // If v was not in S, this edge was previously uncovered.
            // We decrement v's effective degree (count of uncovered incident edges).
            for (int v : adj[best_v]) {
                if (!current_sol[v]) {
                    curr_deg[v]--;
                    rem_edges_count--;
                }
            }
        }

        // 3. Pruning Phase
        // A vertex is redundant if all its neighbors are already in the vertex cover.
        // We shuffle the check order to reach different minimal solutions.
        if (iter > 1) random_shuffle(prune_order.begin(), prune_order.end());
        
        bool improved = true;
        while (improved) {
            improved = false;
            for (int i : prune_order) {
                if (current_sol[i]) {
                    bool needed = false;
                    for (int v : adj[i]) {
                        if (!current_sol[v]) {
                            needed = true;
                            break;
                        }
                    }
                    if (!needed) {
                        current_sol[i] = 0;
                        current_k--;
                        improved = true;
                    }
                }
            }
        }

        // 4. Update Global Best
        if (current_k < min_k) {
            min_k = current_k;
            best_solution = current_sol;
        }
    }

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << best_solution[i] << "\n";
    }

    return 0;
}
#include <iostream>
#include <vector>
#include <algorithm>
#include <random>
#include <chrono>
#include <numeric>

// Optimization pragmas for faster execution
#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

using namespace std;

// Timer
auto start_time = chrono::high_resolution_clock::now();
double get_time() {
    auto now = chrono::high_resolution_clock::now();
    return chrono::duration<double>(now - start_time).count();
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    // Adjacency List for traversal
    vector<vector<int>> adj(N);
    // Adjacency Matrix (Flattened) for O(1) edge check
    // Size N*N. For N=10000, 100MB is acceptable within 512MB limit.
    vector<char> adj_mat(N * N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert 1-based to 0-based
        adj[u].push_back(v);
        adj[v].push_back(u);
        adj_mat[u * N + v] = 1;
        adj_mat[v * N + u] = 1;
    }

    // Random Number Generator
    mt19937 rng(1337);

    // Data structures for solution
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);

    vector<int> current_sol(N);
    vector<int> tightness(N); // tightness[v] = number of neighbors of v in S
    vector<int> best_solution(N, 0);
    int best_k = 0;

    vector<int> one_tight;
    one_tight.reserve(N);
    vector<int> P_u;
    P_u.reserve(N);

    // Main Heuristic Loop
    // We run until we are close to the time limit (1.96s out of 2.0s)
    while (get_time() < 1.96) {
        // 1. Construct Randomized Greedy Solution
        // Shuffle vertices to get random greedy start
        shuffle(p.begin(), p.end(), rng);

        // Reset state
        fill(current_sol.begin(), current_sol.end(), 0);
        fill(tightness.begin(), tightness.end(), 0);
        int current_k = 0;

        // Greedy Construction: Pick node if no neighbors currently selected
        for (int u : p) {
            if (tightness[u] == 0) {
                current_sol[u] = 1;
                current_k++;
                for (int v : adj[u]) {
                    tightness[v]++;
                }
            }
        }

        // 2. Local Search (Hill Climbing)
        // Strategies:
        // - (1, 2)-swap: Remove 1 node u, Add 2 nodes v, w. (Improvement)
        // - (1, 1)-swap: Remove 1 node u, Add 1 node v. (Plateau move to escape local optima)
        
        int plateau_moves = 0;
        const int MAX_PLATEAU = 2000; // Heuristic limit for non-improving moves

        while (true) {
            if (get_time() > 1.98) break;
            
            // Gather nodes NOT in S that have exactly 1 neighbor in S (1-tight)
            one_tight.clear();
            for (int i = 0; i < N; ++i) {
                if (current_sol[i] == 0 && tightness[i] == 1) {
                    one_tight.push_back(i);
                }
            }

            if (one_tight.empty()) break; // No 1-tight nodes means unlikely to find (1,2) swaps easily
            
            // Shuffle to randomize search order
            shuffle(one_tight.begin(), one_tight.end(), rng);

            bool found_improvement = false;
            
            // Try to find a (1,2) swap
            for (int v : one_tight) {
                if (tightness[v] != 1) continue; // Might have changed due to other moves

                // Find the unique neighbor u in S
                int u = -1;
                for (int nbr : adj[v]) {
                    if (current_sol[nbr]) {
                        u = nbr;
                        break;
                    }
                }
                
                if (u == -1) continue; // Should not happen

                // Identify P_u: set of nodes that would become free if u is removed.
                // These are neighbors of u with tightness == 1.
                // v is definitely in P_u.
                P_u.clear();
                for (int nbr : adj[u]) {
                    if (current_sol[nbr] == 0 && tightness[nbr] == 1) {
                        P_u.push_back(nbr);
                    }
                }

                // We need to find two nodes in P_u that are NOT connected.
                // Since v is in P_u, we can specifically look for another w in P_u 
                // such that {v, w} is not an edge.
                int partner = -1;
                if (P_u.size() >= 2) {
                    for (int w : P_u) {
                        if (w == v) continue;
                        // Check if edge exists between v and w
                        if (!adj_mat[v * N + w]) {
                            partner = w;
                            break;
                        }
                    }
                }

                if (partner != -1) {
                    // Found improvement!
                    // Remove u, Add v, Add partner
                    
                    // Remove u
                    current_sol[u] = 0;
                    current_k--;
                    for (int nbr : adj[u]) tightness[nbr]--;

                    // Add v
                    current_sol[v] = 1;
                    current_k++;
                    for (int nbr : adj[v]) tightness[nbr]++;

                    // Add partner
                    current_sol[partner] = 1;
                    current_k++;
                    for (int nbr : adj[partner]) tightness[nbr]++;

                    found_improvement = true;
                    plateau_moves = 0; // Reset plateau counter
                    break; // Restart loop to refresh one_tight
                }
            }

            if (found_improvement) continue;

            // If no improvement found, try a plateau move to perturb solution
            // Swap a random 1-tight node v with its neighbor u
            if (plateau_moves < MAX_PLATEAU && !one_tight.empty()) {
                int v = one_tight[0]; // Random because shuffled
                int u = -1;
                for (int nbr : adj[v]) {
                    if (current_sol[nbr]) {
                        u = nbr;
                        break;
                    }
                }

                if (u != -1) {
                    // Swap u -> v
                    current_sol[u] = 0;
                    for (int nbr : adj[u]) tightness[nbr]--;
                    current_sol[v] = 1;
                    for (int nbr : adj[v]) tightness[nbr]++;
                    
                    plateau_moves++;
                } else {
                    // Should theoretically not happen given tightness logic
                    break;
                }
            } else {
                // Stuck and plateau limit reached, restart with new random greedy
                break;
            }
        }

        // Update Global Best
        if (current_k > best_k) {
            best_k = current_k;
            best_solution = current_sol;
        }
    }

    // Output result
    for (int i = 0; i < N; ++i) {
        cout << best_solution[i] << "\n";
    }

    return 0;
}
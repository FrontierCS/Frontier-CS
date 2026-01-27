#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>
#include <chrono>

using namespace std;

// Global variables for graph and state
int N, M;
vector<vector<int>> adj;
vector<char> adjMat; // Flattened adjacency matrix: adjMat[u * N + v] stores edge {u, v} with u < v

// Current solution state
vector<bool> in_set;
vector<int> tightness; // tightness[v] = number of neighbors of v currently in S
int current_k = 0;

// Best solution found
vector<bool> best_in_set;
int best_k = -1;

// Random number generator
mt19937 rng(1337);

// Function to check edge existence
// u and v are 0-based
inline bool is_edge(int u, int v) {
    if (u > v) swap(u, v);
    return adjMat[u * N + v];
}

// Add vertex u to S
// Precondition: u is not in S, and no neighbors of u are in S (tightness[u] == 0)
void add_vertex(int u) {
    in_set[u] = true;
    for (int v : adj[u]) {
        tightness[v]++;
    }
}

// Remove vertex u from S
// Precondition: u is in S
void remove_vertex(int u) {
    in_set[u] = false;
    for (int v : adj[u]) {
        tightness[v]--;
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    // Initialize adjacency list
    adj.resize(N);
    // Initialize adjacency matrix (flattened)
    // N <= 10000, so N*N <= 100,000,000 bytes (approx 95 MB), fits in memory
    adjMat.assign(N * N, 0);

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert to 0-based indexing
        adj[u].push_back(v);
        adj[v].push_back(u);
        
        if (u > v) swap(u, v);
        adjMat[u * N + v] = 1;
    }

    in_set.resize(N, false);
    tightness.resize(N, 0);
    best_in_set.resize(N, false);

    // Timing setup
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.95; // seconds, slightly less than 2.0s to be safe

    // Pre-allocate vectors to reuse memory
    vector<int> candidates;
    candidates.reserve(N);
    vector<int> c_u;
    c_u.reserve(N);
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);

    // Main optimization loop (Iterated Local Search)
    while (true) {
        // Check time limit
        auto curr_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = curr_time - start_time;
        if (elapsed.count() > time_limit) break;

        // Reset state for a new restart
        fill(in_set.begin(), in_set.end(), false);
        fill(tightness.begin(), tightness.end(), 0);
        current_k = 0;
        
        // Randomize vertex order for greedy construction
        shuffle(p.begin(), p.end(), rng);

        // Greedy construction phase: Add vertices if they don't conflict
        for (int i : p) {
            if (tightness[i] == 0) {
                add_vertex(i);
                current_k++;
            }
        }

        // Local Search Improvement Phase
        bool improved = true;
        while (improved) {
            improved = false;

            // Step 1: Fill 0-tightness nodes (Greedy Packing)
            // If any node becomes free (tightness 0), add it immediately
            for (int i = 0; i < N; ++i) {
                if (!in_set[i] && tightness[i] == 0) {
                    add_vertex(i);
                    current_k++;
                    improved = true;
                }
            }
            if (improved) continue;

            // Step 2: Try (1, 2) swaps
            // Identify a vertex u in S. If we remove u, can we add two neighbors v, w?
            // This requires v, w to have tightness 1 (connected only to u in S) and {v, w} not an edge.
            
            // Collect vertices in S
            candidates.clear();
            for (int i = 0; i < N; ++i) {
                if (in_set[i]) candidates.push_back(i);
            }
            
            // Random shuffle to avoid bias
            shuffle(candidates.begin(), candidates.end(), rng);

            for (int u : candidates) {
                // Find candidates for replacement: neighbors of u not in S with tightness 1
                c_u.clear();
                for (int v : adj[u]) {
                    if (!in_set[v] && tightness[v] == 1) {
                        c_u.push_back(v);
                    }
                }

                if (c_u.size() < 2) continue;

                int v_sel = -1, w_sel = -1;

                // Check for a non-edge pair in c_u (Independent Set of size 2)
                // If c_u is small, use exhaustive search. If large, use random sampling.
                if (c_u.size() <= 50) {
                    for (size_t i = 0; i < c_u.size(); ++i) {
                        for (size_t j = i + 1; j < c_u.size(); ++j) {
                            if (!is_edge(c_u[i], c_u[j])) {
                                v_sel = c_u[i];
                                w_sel = c_u[j];
                                goto found_swap;
                            }
                        }
                    }
                } else {
                    int tries = 100;
                    while (tries--) {
                        int i = rng() % c_u.size();
                        int j = rng() % c_u.size();
                        if (i == j) continue;
                        if (!is_edge(c_u[i], c_u[j])) {
                            v_sel = c_u[i];
                            w_sel = c_u[j];
                            goto found_swap;
                        }
                    }
                }
                
                found_swap:;
                
                if (v_sel != -1) {
                    // Perform (1, 2) swap
                    remove_vertex(u);
                    add_vertex(v_sel);
                    add_vertex(w_sel);
                    current_k++;
                    improved = true;
                    // Break inner loop to restart filling 0-tightness nodes
                    break; 
                }
            }
            
            if (improved) continue;

            // Step 3: (1, 1) Plateau moves (Perturbation)
            // Try swapping u (in S) with v (not in S, tight=1, neighbor of u).
            // This doesn't change size immediately but changes configuration to potentially enable Step 1.
            
            int plateau_steps = N; 
            bool plateau_success = false;
            
            for (int k = 0; k < plateau_steps; ++k) {
                // Find a random v not in S with tightness 1
                int v = -1;
                for (int t = 0; t < 10; ++t) {
                    int r = rng() % N;
                    if (!in_set[r] && tightness[r] == 1) {
                        v = r;
                        break;
                    }
                }
                
                if (v == -1) continue; 

                // Find its unique neighbor u in S
                int u = -1;
                for (int nb : adj[v]) {
                    if (in_set[nb]) {
                        u = nb;
                        break;
                    }
                }
                
                if (u == -1) continue; 

                // Swap u -> v
                remove_vertex(u);
                add_vertex(v);
                
                // Check if this move created any opportunity (tightness 0 nodes)
                // We only need to check neighbors of the removed vertex u
                bool found_opportunity = false;
                for (int nb : adj[u]) {
                    if (!in_set[nb] && tightness[nb] == 0) {
                        add_vertex(nb);
                        current_k++;
                        found_opportunity = true;
                        break;
                    }
                }
                
                if (found_opportunity) {
                    improved = true;
                    plateau_success = true;
                    break;
                }
            }
            
            if (plateau_success) continue;
            
            // If no improvements found after all steps, we are locally optimal
            break;
        }

        // Update global best solution
        if (current_k > best_k) {
            best_k = current_k;
            best_in_set = in_set;
        }
    }

    // Output the best solution found
    for (int i = 0; i < N; ++i) {
        cout << (best_in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}
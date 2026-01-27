#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

// Function for fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Global variables for the graph and solution state
int N, M;
vector<vector<int>> adj;
vector<int> current_sol;
vector<int> conflict; // conflict[u] = counts how many neighbors of u are currently in S
int current_k = 0;

vector<int> best_sol;
int best_k = -1;

// Helper: Add u to S
// Precondition: u is not in S, and usually conflict[u] == 0
inline void add_vertex(int u) {
    if (current_sol[u]) return;
    current_sol[u] = 1;
    current_k++;
    for (int v : adj[u]) {
        conflict[v]++;
    }
}

// Helper: Remove u from S
inline void remove_vertex(int u) {
    if (!current_sol[u]) return;
    current_sol[u] = 0;
    current_k--;
    for (int v : adj[u]) {
        conflict[v]--;
    }
}

// Greedily fill the current solution with any available vertices
// Iterates through a provided permutation to determine order
void full_greedy_fill(const vector<int>& p) {
    for (int u : p) {
        if (!current_sol[u] && conflict[u] == 0) {
            add_vertex(u);
        }
    }
}

int main() {
    fast_io();

    if (!(cin >> N >> M)) return 0;

    adj.resize(N + 1);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Deduplicate edges to ensure conflict counting is accurate (1 per neighbor)
    for (int i = 1; i <= N; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }

    current_sol.assign(N + 1, 0);
    conflict.assign(N + 1, 0);
    best_sol.assign(N + 1, 0);

    // Initialize random number generator
    auto seed = chrono::steady_clock::now().time_since_epoch().count();
    mt19937 rng(seed);
    
    // Vector for random iteration
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);

    auto start_time = chrono::steady_clock::now();
    double time_limit = 1.96; // Slightly under 2.0s

    // Main optimization loop with restarts
    while (true) {
        // Check global time limit
        double total_elapsed = chrono::duration_cast<chrono::duration<double>>(
            chrono::steady_clock::now() - start_time).count();
        if (total_elapsed > time_limit) break;

        // --- Restart Phase ---
        // Reset buffers
        fill(current_sol.begin(), current_sol.end(), 0);
        fill(conflict.begin(), conflict.end(), 0);
        current_k = 0;

        // Create initial maximal independent set randomly
        shuffle(p.begin(), p.end(), rng);
        full_greedy_fill(p);

        // Update best found so far
        if (current_k > best_k) {
            best_k = current_k;
            best_sol = current_sol;
        }

        // --- Local Search Phase ---
        // Iterate to improve the solution
        int steps = 0;
        // Adjust these parameters based on N or performance tuning
        // Approx 100k-500k steps per restart usually fits
        const int MAX_STEPS = 500000; 
        const int TIME_CHECK_MASK = 1023;

        while (steps < MAX_STEPS) {
            steps++;
            // Check time occasionally inside the tight loop
            if ((steps & TIME_CHECK_MASK) == 0) {
                 total_elapsed = chrono::duration_cast<chrono::duration<double>>(
                    chrono::steady_clock::now() - start_time).count();
                 if (total_elapsed > time_limit) break;
            }

            // Pick a random vertex v randomly
            int v = (rng() % N) + 1;
            
            // If already in S, nothing to do
            if (current_sol[v]) continue;

            // Use the "conflict" count to determine move type
            int c = conflict[v];

            if (c == 1) {
                // (1, 1) Swap: Vertex outside has 1 neighbor inside.
                // Swap them: remove neighbor u, add v.
                // This maintains size, but changes configuration (Plateau Search).
                
                int u = -1;
                // Find the single neighbor u in S
                for (int nb : adj[v]) {
                    if (current_sol[nb]) {
                        u = nb;
                        break;
                    }
                }

                if (u != -1) {
                    remove_vertex(u);
                    add_vertex(v);

                    // Check if removing u opened up spots for other nodes
                    // Only neighbors of u could have conflict count drop to 0
                    for (int nb : adj[u]) {
                        // Check if valid to add
                        if (!current_sol[nb] && conflict[nb] == 0) {
                            add_vertex(nb);
                        }
                    }

                    if (current_k > best_k) {
                        best_k = current_k;
                        best_sol = current_sol;
                    }
                }
            } 
            else if (c == 2) {
                // (1, 2) Swap: Vertex has 2 neighbors inside.
                // Remove 2, Add 1 -> Net size change: -1.
                // This is a "bad" move, but helps escape local optima (Simulated Annealing).
                // Perform with low probability.
                
                if ((rng() & 255) == 0) { // ~0.4% probability
                    int u1 = -1, u2 = -1;
                    // Identify the two neighbors
                    for (int nb : adj[v]) {
                        if (current_sol[nb]) {
                            if (u1 == -1) u1 = nb;
                            else { u2 = nb; break; }
                        }
                    }

                    if (u1 != -1 && u2 != -1) {
                        remove_vertex(u1);
                        remove_vertex(u2);
                        add_vertex(v);

                        // Greedily fill any holes created by removing u1 and u2
                        for (int nb : adj[u1]) if (!current_sol[nb] && conflict[nb] == 0) add_vertex(nb);
                        for (int nb : adj[u2]) if (!current_sol[nb] && conflict[nb] == 0) add_vertex(nb);

                        if (current_k > best_k) {
                            best_k = current_k;
                            best_sol = current_sol;
                        }
                    }
                }
            }
            // else if c == 0:
            //   If c == 0, v should have been added. 
            //   This case is handled by filling holes immediately after removals.
            //   However, if we randomly pick a vertex that is free, add it.
            else if (c == 0) {
                add_vertex(v);
                if (current_k > best_k) {
                    best_k = current_k;
                    best_sol = current_sol;
                }
            }
        }
    }

    // Output the best solution found
    for (int i = 1; i <= N; ++i) {
        cout << best_sol[i] << "\n";
    }

    return 0;
}
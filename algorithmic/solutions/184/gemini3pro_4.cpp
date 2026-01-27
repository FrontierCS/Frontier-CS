#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <ctime>
#include <chrono>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

// Graph data
int N, M;
vector<int> adj[MAXN];

// Current solution state
// in_set[i] is true if vertex i is in the current independent set S
bool in_set[MAXN];
// neighbor_counts[i] stores the number of neighbors of vertex i that are currently in S
// A vertex i can be added to S if and only if neighbor_counts[i] == 0
int neighbor_counts[MAXN]; 

// Best solution found so far
bool best_in_set[MAXN];
int best_k = -1;

// Random number generator
mt19937 rng(1337);

// Function to add vertex u to the independent set S
// Precondition: u is not in S and neighbor_counts[u] == 0
void add(int u) {
    if (in_set[u]) return;
    in_set[u] = true;
    for (int v : adj[u]) {
        neighbor_counts[v]++;
    }
}

// Function to remove vertex u from S
void remove(int u) {
    if (!in_set[u]) return;
    in_set[u] = false;
    for (int v : adj[u]) {
        neighbor_counts[v]--;
    }
}

// Save current solution if it's the best seen so far
void save_best() {
    int current_k = 0;
    for (int i = 1; i <= N; ++i) {
        if (in_set[i]) current_k++;
    }
    if (current_k > best_k) {
        best_k = current_k;
        for (int i = 1; i <= N; ++i) best_in_set[i] = in_set[i];
    }
}

// Greedy fill: iterate and add any vertex that is valid to make the set Maximal
void fill_greedy() {
    vector<int> candidates;
    candidates.reserve(N);
    for (int i = 1; i <= N; ++i) {
        if (!in_set[i] && neighbor_counts[i] == 0) {
            candidates.push_back(i);
        }
    }
    
    if (candidates.empty()) return;

    // Shuffle to ensure diversity in greedy choices
    shuffle(candidates.begin(), candidates.end(), rng);
    
    for (int u : candidates) {
        // Double check because adding a previous candidate might have blocked this one
        if (!in_set[u] && neighbor_counts[u] == 0) {
            add(u);
        }
    }
}

// Reset solution to empty
void clear_solution() {
    for (int i = 1; i <= N; ++i) {
        in_set[i] = false;
        neighbor_counts[i] = 0;
    }
}

// Build a solution using a random permutation greedy strategy
void build_random_greedy() {
    clear_solution();
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    shuffle(p.begin(), p.end(), rng);

    for (int u : p) {
        if (neighbor_counts[u] == 0) {
            add(u);
        }
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        // Input vertices are 1-based. Multiple edges allowed by problem statement.
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    auto start_time = chrono::steady_clock::now();

    // Initial solution
    build_random_greedy();
    save_best();

    // Main optimization loop (Iterated Local Search)
    long long iter_count = 0;
    while (true) {
        iter_count++;
        // Check time limit periodically (every 256 iterations)
        if ((iter_count & 255) == 0) {
            auto curr_time = chrono::steady_clock::now();
            chrono::duration<double> elapsed = curr_time - start_time;
            if (elapsed.count() > 1.95) break; // Leave a small margin before 2.0s
        }

        // Restart occasionally to explore different basins of attraction
        if (iter_count % 3000 == 0) {
            build_random_greedy();
            save_best();
            continue;
        }

        // --- Local Search Phase ---
        
        // 1. Try to extend the current set (make it maximal)
        fill_greedy();
        save_best();

        // 2. Try (1, 1) swaps to escape plateaus
        // A vertex u not in S with neighbor_counts[u] == 1 is a candidate.
        // We can swap u with its unique neighbor v in S.
        vector<int> swap_candidates;
        swap_candidates.reserve(N);
        for (int i = 1; i <= N; ++i) {
            if (!in_set[i] && neighbor_counts[i] == 1) {
                swap_candidates.push_back(i);
            }
        }

        bool improvement_found_in_swap = false;
        if (!swap_candidates.empty()) {
            shuffle(swap_candidates.begin(), swap_candidates.end(), rng);
            
            // Limit number of swaps per iteration to balance exploration/speed
            int swaps_tried = 0;
            int max_swaps = 10 + N / 20; 

            for (int u : swap_candidates) {
                if (swaps_tried >= max_swaps) break;
                // Verify condition (state might have changed)
                if (in_set[u] || neighbor_counts[u] != 1) continue;

                // Find the unique neighbor v in S
                int v = -1;
                for (int nb : adj[u]) {
                    if (in_set[nb]) {
                        v = nb;
                        break;
                    }
                }
                
                if (v != -1) {
                    // Perform the swap
                    remove(v);
                    add(u);
                    swaps_tried++;

                    // Check if this swap allows adding NEW vertices
                    // Removing v unblocks its neighbors. Adding u blocks its neighbors.
                    // We check neighbors of v to see if any became free (count == 0).
                    vector<int> potential_adds;
                    for (int nb : adj[v]) {
                        if (!in_set[nb] && neighbor_counts[nb] == 0) {
                            potential_adds.push_back(nb);
                        }
                    }
                    
                    if (!potential_adds.empty()) {
                        bool added_extra = false;
                        for (int pa : potential_adds) {
                            if (!in_set[pa] && neighbor_counts[pa] == 0) {
                                add(pa);
                                added_extra = true;
                            }
                        }
                        if (added_extra) {
                            improvement_found_in_swap = true;
                            save_best();
                            // Fill any other openings
                            fill_greedy(); 
                            save_best();
                            break; // Break swap loop to return to main loop
                        }
                    }
                }
            }
        }

        if (improvement_found_in_swap) continue;

        // --- Perturbation Phase ---
        // If no immediate improvement, we are likely in a local optimum.
        // Perturb the solution by removing a few random vertices.
        vector<int> current_s;
        current_s.reserve(N);
        for (int i = 1; i <= N; ++i) {
            if (in_set[i]) current_s.push_back(i);
        }

        if (!current_s.empty()) {
            int k = 1 + (rng() % 3); // Remove 1 to 3 vertices
            shuffle(current_s.begin(), current_s.end(), rng);
            for (int i = 0; i < k && i < (int)current_s.size(); ++i) {
                remove(current_s[i]);
            }
            // Next iteration will start with fill_greedy to repair the solution
        } else {
            build_random_greedy();
        }
    }

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << (best_in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}
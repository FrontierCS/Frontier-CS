#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <random>
#include <cstring>

using namespace std;

// Constants and Globals
const int MAXN = 1005;
int N, M;

// Adjacency Matrix for O(1) edge checks
bool adj_mat[MAXN][MAXN];
// Adjacency List for iterating neighbors
vector<int> adj_list[MAXN];

// Current solution state
// in_set[i] = true if vertex i is in the independent set
bool in_set[MAXN];
// neighbor_f[i] = number of neighbors of i that are currently in the independent set
int neighbor_f[MAXN]; 

// Best solution found so far
bool best_in_set[MAXN];
int max_size = 0;

// Random number generator
mt19937 rng(1337);

// Adds vertex u to the set S
void add_vertex(int u, vector<int>& s_list) {
    if (in_set[u]) return;
    in_set[u] = true;
    s_list.push_back(u);
    for (int v : adj_list[u]) {
        neighbor_f[v]++;
    }
}

// Removes vertex u from the set S
void remove_vertex(int u, vector<int>& s_list) {
    if (!in_set[u]) return;
    in_set[u] = false;
    // Remove u from s_list by swapping with the last element
    for (size_t i = 0; i < s_list.size(); ++i) {
        if (s_list[i] == u) {
            s_list[i] = s_list.back();
            s_list.pop_back();
            break;
        }
    }
    for (int v : adj_list[u]) {
        neighbor_f[v]--;
    }
}

// Helper to get elapsed time in seconds
inline double get_time() {
    return (double)clock() / CLOCKS_PER_SEC;
}

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    // Reset Data
    memset(adj_mat, 0, sizeof(adj_mat));
    for (int i = 0; i < N; ++i) adj_list[i].clear();

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        // Convert 1-based to 0-based
        u--; v--;
        if (u != v && !adj_mat[u][v]) {
            adj_mat[u][v] = adj_mat[v][u] = true;
            adj_list[u].push_back(v);
            adj_list[v].push_back(u);
        }
    }

    // Array for randomized iteration order
    vector<int> p(N);
    iota(p.begin(), p.end(), 0);

    max_size = 0;
    double start_time = get_time();
    
    // Main Optimization Loop: Run for slightly less than 2.0s
    while (get_time() - start_time < 1.95) {
        // --- Initialization Phase ---
        // Clear current state
        fill(in_set, in_set + N, false);
        fill(neighbor_f, neighbor_f + N, 0);
        vector<int> current_s;
        current_s.reserve(N);

        // Randomized Greedy Construction
        shuffle(p.begin(), p.end(), rng);
        for (int x : p) {
            if (neighbor_f[x] == 0) {
                add_vertex(x, current_s);
            }
        }

        // Update Best
        if ((int)current_s.size() > max_size) {
            max_size = current_s.size();
            copy(in_set, in_set + N, best_in_set);
        }

        // --- Local Search Phase ---
        int stagnation = 0;
        int MAX_STAGNATION = N; // Parameter to control restart frequency

        while (stagnation < MAX_STAGNATION && get_time() - start_time < 1.95) {
            bool improved = false;

            // 1. ADD (0->1): Try to add any free vertices
            // Checking all vertices might be slightly redundant, 
            // but necessary after swaps open up space.
            // Using a randomized permutation to avoid bias.
            
            // To be efficient, we track improvement.
            bool added_any = false;
            for (int x : p) {
                if (!in_set[x] && neighbor_f[x] == 0) {
                    add_vertex(x, current_s);
                    added_any = true;
                }
            }

            if (added_any) {
                improved = true;
                stagnation = 0;
                if ((int)current_s.size() > max_size) {
                    max_size = current_s.size();
                    copy(in_set, in_set + N, best_in_set);
                }
                // If we added nodes, just loop back to see if we can add more or optimize
                continue; 
            }

            // 2. SWAP (1->2): Try to replace 1 vertex u with 2 vertices {v1, v2}
            // Candidates for {v1, v2} must have neighbor_f == 1 (conflict only with u).
            shuffle(current_s.begin(), current_s.end(), rng);
            
            bool swap_1_2 = false;
            for (int u : current_s) {
                // Collect potential replacements for u
                // A vertex v is a candidate if it is not in S, and its only neighbor in S is u.
                // This implies neighbor_f[v] == 1 and u is a neighbor of v.
                vector<int> candidates;
                // Heuristic: Reserve rough size to avoid reallocations
                candidates.reserve(adj_list[u].size()); 
                
                for (int v : adj_list[u]) {
                    if (neighbor_f[v] == 1) { 
                        candidates.push_back(v);
                    }
                }

                // We need to find two candidates that are not connected
                if (candidates.size() >= 2) {
                    int c1 = -1, c2 = -1;
                    // Check pairs. First pair found is sufficient.
                    // This is O(d(u)^2), can be heavy for dense graphs, but worth it.
                    for (size_t i = 0; i < candidates.size(); ++i) {
                        for (size_t j = i + 1; j < candidates.size(); ++j) {
                            int v1 = candidates[i];
                            int v2 = candidates[j];
                            if (!adj_mat[v1][v2]) {
                                c1 = v1; c2 = v2;
                                goto found_pair;
                            }
                        }
                    }
                    found_pair:;
                    
                    if (c1 != -1) {
                        // Apply 1->2 Swap
                        remove_vertex(u, current_s); 
                        add_vertex(c1, current_s);
                        add_vertex(c2, current_s);
                        swap_1_2 = true;
                        break; // current_s changed, break loop
                    }
                }
            }

            if (swap_1_2) {
                improved = true;
                stagnation = 0;
                if ((int)current_s.size() > max_size) {
                    max_size = current_s.size();
                    copy(in_set, in_set + N, best_in_set);
                }
                continue; 
            }

            // 3. PERTURB (1->1): Force a swap to explore
            if (!improved) {
                stagnation++;
                // Try a small number of random 1-1 swaps to shake state
                // This maintains size but changes configuration, potentially enabling future improvements.
                if (!current_s.empty()) {
                    int u = current_s[uniform_int_distribution<int>(0, (int)current_s.size()-1)(rng)];
                    
                    // Find swappable neighbors
                    vector<int> swappable;
                    for (int v : adj_list[u]) {
                        if (neighbor_f[v] == 1) { // neighbor_f[v]==1 implies only conflict is u
                            swappable.push_back(v);
                        }
                    }
                    
                    if (!swappable.empty()) {
                        int v = swappable[uniform_int_distribution<int>(0, (int)swappable.size()-1)(rng)];
                        remove_vertex(u, current_s);
                        add_vertex(v, current_s);
                        // We reset stagnation slightly or just treat it as a step
                        // Here we count it as stagnation towards restart, but it changes state.
                    }
                }
            }
        }
    }

    // Output Result
    for (int i = 0; i < N; ++i) {
        cout << (best_in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}
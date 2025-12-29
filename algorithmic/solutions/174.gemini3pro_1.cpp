#include <iostream>
#include <vector>
#include <algorithm>
#include <ctime>
#include <cstdlib>
#include <random>
#include <numeric>

using namespace std;

// Set time limit to 0.95 seconds to safely finish within a typical 1s limit.
const double TIME_LIMIT = 0.95; 

int n, m;
vector<int> adj[1001];
int color[1001];      // Current working color assignment
int best_color[1001]; // Best assignment found so far
int min_conflicts = 2000000000;

// Function to calculate total conflicts for the whole graph from scratch
int count_all_conflicts() {
    int conflicts = 0;
    for (int u = 1; u <= n; ++u) {
        for (int v : adj[u]) {
            // Count each edge once
            if (u < v && color[u] == color[v]) {
                conflicts++;
            }
        }
    }
    return conflicts;
}

// Function to calculate conflicts for a specific node u given it has color c
// This counts edges (u, v) where color[v] == c
int get_node_conflicts(int u, int c) {
    int cnt = 0;
    for (int v : adj[u]) {
        if (color[v] == c) {
            cnt++;
        }
    }
    return cnt;
}

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    // Handle edge case where there are no edges
    if (m == 0) {
        for (int i = 1; i <= n; ++i) {
            cout << 1 << (i == n ? "" : " ");
        }
        cout << "\n";
        return 0;
    }

    // Initialize random number generator
    // Using mt19937 for better randomness than rand()
    mt19937 rng(time(0));
    uniform_int_distribution<int> dist(1, 3);

    // Initial random assignment
    for (int i = 1; i <= n; ++i) {
        color[i] = dist(rng);
    }
    
    // Compute initial score
    int current_total_conflicts = count_all_conflicts();
    
    // Initialize best solution
    min_conflicts = current_total_conflicts;
    for(int i = 1; i <= n; ++i) best_color[i] = color[i];

    clock_t start_time = clock();
    
    // Vector of nodes to iterate in random order
    vector<int> nodes(n);
    iota(nodes.begin(), nodes.end(), 1);

    // Hill Climbing with Random Restarts
    // Run until time limit is nearly reached
    while ((double)(clock() - start_time) / CLOCKS_PER_SEC < TIME_LIMIT) {
        bool improved_pass = false;
        
        // Shuffle node order for this pass to avoid cyclic biases
        shuffle(nodes.begin(), nodes.end(), rng);
        
        for (int u : nodes) {
            int current_c = color[u];
            int current_cost = get_node_conflicts(u, current_c);
            
            int best_c = current_c;
            int best_local_cost = current_cost;
            
            // Randomize order of checking colors to avoid bias towards lower indices in ties
            int candidates[3] = {1, 2, 3};
            for (int i = 0; i < 3; ++i) {
                int j = i + (rng() % (3 - i));
                swap(candidates[i], candidates[j]);
            }

            // Try changing color of u to minimize local conflicts
            for (int k = 0; k < 3; ++k) {
                int c = candidates[k];
                if (c == current_c) continue;
                
                int cost = get_node_conflicts(u, c);
                if (cost < best_local_cost) {
                    best_local_cost = cost;
                    best_c = c;
                }
            }
            
            // If we found a better color for u
            if (best_c != current_c) {
                // Update total conflicts incrementally:
                // Subtract old conflicts involving u, add new conflicts involving u
                current_total_conflicts -= (current_cost - best_local_cost);
                color[u] = best_c;
                improved_pass = true;
                
                // Update global best if this state is better
                if (current_total_conflicts < min_conflicts) {
                    min_conflicts = current_total_conflicts;
                    for(int i = 1; i <= n; ++i) best_color[i] = color[i];
                    
                    // If we found a perfect solution (0 conflicts), we can stop early
                    if (min_conflicts == 0) goto end_search; 
                }
            }
        }
        
        // If a full pass over all nodes resulted in no changes, we are in a local optimum.
        // Restart with a completely new random assignment to explore other areas of the search space.
        if (!improved_pass) {
            for (int i = 1; i <= n; ++i) {
                color[i] = dist(rng);
            }
            // Recalculate total score for the new start
            current_total_conflicts = count_all_conflicts();
            
            // Check if this random start happens to be better
            if (current_total_conflicts < min_conflicts) {
                min_conflicts = current_total_conflicts;
                for(int i = 1; i <= n; ++i) best_color[i] = color[i];
                if (min_conflicts == 0) goto end_search;
            }
        }
    }

    end_search:;

    // Output the best coloring found
    for (int i = 1; i <= n; ++i) {
        cout << best_color[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}
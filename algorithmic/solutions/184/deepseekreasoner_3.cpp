#pragma GCC optimize("O3,unroll-loops")
#pragma GCC target("avx2,bmi,bmi2,lzcnt,popcnt")

#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <ctime>
#include <cstdlib>

using namespace std;

// Maximum number of vertices as per constraints
const int MAXN = 1005;

// Global Data Structures
int n, m;
vector<int> adj[MAXN];          // Adjacency list
int conflict[MAXN];             // Number of neighbors currently in S
bool in_set[MAXN];              // Current solution status
vector<int> not_in_set;         // Set of vertices NOT in S (for efficient random selection)
int pos_in_not_set[MAXN];       // Map vertex ID to position in not_in_set

int current_k = 0;              // Current size of S
bool best_in_set[MAXN];         // Best solution found (snapshot)
int best_k = -1;                // Size of best solution

vector<int> free_nodes;         // Stack for vertices with 0 conflicts

// Fast Random Generator (Linear Congruential Generator)
unsigned int seed = 123456789;
unsigned int fast_rand() {
    seed = seed * 1664525u + 1013904223u;
    return seed;
}

// Function to safely remove a node from the Independent Set
void remove_node(int u) {
    if (!in_set[u]) return;
    in_set[u] = false;
    current_k--;
    
    // Add u back to not_in_set
    pos_in_not_set[u] = not_in_set.size();
    not_in_set.push_back(u);

    // Update neighbors
    for (int v : adj[u]) {
        conflict[v]--;
        // If v becomes free (0 conflicts) and is not in set, it's a candidate
        if (conflict[v] == 0 && !in_set[v]) {
            free_nodes.push_back(v);
        }
    }
}

// Function to safely add a node to the Independent Set
void add_node(int u) {
    if (in_set[u]) return;
    in_set[u] = true;
    current_k++;
    
    // Remove u from not_in_set
    // Standard swap-and-pop O(1) removal
    int last = not_in_set.back();
    int p = pos_in_not_set[u];
    not_in_set[p] = last;
    pos_in_not_set[last] = p;
    not_in_set.pop_back();
    
    // Update neighbors
    for (int v : adj[u]) {
        conflict[v]++;
    }
}

// Iteratively add any nodes that have 0 conflicts
void greedy_fill() {
    while (!free_nodes.empty()) {
        int u = free_nodes.back();
        free_nodes.pop_back();
        
        // Double check conditions: might have been invalidated by recent adds in this loop
        if (!in_set[u] && conflict[u] == 0) {
            add_node(u);
        }
    }
}

// Force a node v into the set, removing its blocking neighbors (1 or 2 typically)
void force_add(int v) {
    // Identify blocking neighbors
    // We use a static buffer to avoid repeated allocation
    static vector<int> to_remove;
    to_remove.clear();
    
    for (int u : adj[v]) {
        if (in_set[u]) {
            to_remove.push_back(u);
        }
    }
    
    // Remove blockers
    for (int u : to_remove) {
        remove_node(u);
    }
    
    // Add the node v
    add_node(v);
    
    // Fill any gaps created (greedy repair)
    greedy_fill();
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m)) return 0;

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v; // Convert to 0-based indexing
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    
    // Timer setup
    clock_t start_time = clock();
    double time_limit = 1.98; // Close to 2.0s
    
    // Initial seed
    seed = time(NULL);

    int restart_count = 0;
    
    // Main Optimization Loop (Randomized Local Search with Restarts)
    while (true) {
        // Global time check
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC >= time_limit) break;
        
        restart_count++;
        
        // Reset State for Restart
        current_k = 0;
        for(int i=0; i<n; ++i) {
            in_set[i] = false;
            conflict[i] = 0; // Reset neighbor counts
        }
        not_in_set.resize(n);
        iota(not_in_set.begin(), not_in_set.end(), 0);
        for(int i=0; i<n; ++i) pos_in_not_set[i] = i;
        free_nodes.clear();
        
        // Initial Construction: Randomized Greedy
        vector<int> p(n);
        iota(p.begin(), p.end(), 0);
        // Shuffle vertices
        for (int i = n - 1; i > 0; --i) {
            int j = fast_rand() % (i + 1);
            swap(p[i], p[j]);
        }
        
        // Construct maximal independent set
        for (int u : p) {
            if (conflict[u] == 0) {
                add_node(u);
            }
        }
        
        // Update global best if this construction is better
        if (current_k > best_k) {
            best_k = current_k;
            for(int i=0; i<n; ++i) best_in_set[i] = in_set[i];
        }
        
        // Local Search (Simulated Annealing/Hill Climbing hybrid)
        int no_improve = 0;
        int max_no_improve = 25000; // Threshold to trigger restart
        
        while (true) {
            // Check time occasionally to avoid overhead
            if ((no_improve & 1023) == 0) {
                 if ((double)(clock() - start_time) / CLOCKS_PER_SEC >= time_limit) break;
            }
            if (no_improve > max_no_improve) break; // Trigger restart
            
            if (not_in_set.empty()) break; 
            
            // Pick random candidate not in set
            int idx = fast_rand() % not_in_set.size();
            int v = not_in_set[idx];
            int c = conflict[v];
            
            bool accept = false;
            
            // Heuristic Transition Rules
            if (c == 1) {
                // (1, 1)-swap: Plateau move, always accept to explore
                accept = true;
            } else if (c == 2) {
                // (1, 2)-swap: Decrease size by 1, accept with low probability to escape local optima
                if ((fast_rand() & 255) < 12) { // ~5% probability
                    accept = true;
                }
            }
            // c >= 3 is generally too expensive (size -2), so we ignore
            
            if (accept) {
                force_add(v); // This replaces 1 or 2 nodes with v, then fills free spots
                
                if (current_k > best_k) {
                    best_k = current_k;
                    for(int i=0; i<n; ++i) best_in_set[i] = in_set[i];
                    no_improve = 0;
                } else {
                    no_improve++;
                }
                // Note: If size decreased, we simply continue searching from the new state. 
                // The greedy_fill helps recover size quickly.
            } else {
                no_improve++;
            }
        }
    }

    // Output Result
    for (int i = 0; i < n; ++i) {
        cout << (best_in_set[i] ? 1 : 0) << "\n";
    }

    return 0;
}
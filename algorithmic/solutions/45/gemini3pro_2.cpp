/*
    Problem: Balanced Graph Partitioning (DIMACS10-style)
    Solution: Recursive Bisection with BFS initialization and FM-style refinement
*/
#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <utility>

using namespace std;

// Global variables
int n, m, k_parts;
double eps_val;
vector<vector<int>> adj;
vector<int> p;          // Partition assignment for each node
vector<int> perm;       // Permutation of nodes for recursive processing
vector<int> side;       // Temporary array to store side (0 or 1)
vector<int> subset_flag;// To mark nodes in the current recursion subset
int subset_token = 0;   // Token to validate subset_flag

// Function to read input and build the graph
void read_input() {
    if (scanf("%d %d %d %lf", &n, &m, &k_parts, &eps_val) != 4) return;
    adj.assign(n, vector<int>());
    for (int i = 0; i < m; ++i) {
        int u, v;
        if (scanf("%d %d", &u, &v) != 2) break;
        if (u == v) continue; // Ignore self-loops
        --u; --v; // Convert to 0-based
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
    // Normalize graph: remove duplicate edges and sort adjacency lists
    for (int i = 0; i < n; ++i) {
        sort(adj[i].begin(), adj[i].end());
        adj[i].erase(unique(adj[i].begin(), adj[i].end()), adj[i].end());
    }
}

// Helper to check if edge exists between u and v
// Assumes adj is sorted
bool is_connected(int u, int v) {
    const vector<int>& neighbors = adj[u];
    auto it = lower_bound(neighbors.begin(), neighbors.end(), v);
    return it != neighbors.end() && *it == v;
}

// Recursive function to partition the graph
void solve(int l, int r, int k_sub, int base_id) {
    // Base case: if k=1, assign all nodes in current range to base_id
    if (k_sub == 1) {
        for (int i = l; i < r; ++i) {
            p[perm[i]] = base_id;
        }
        return;
    }
    if (l >= r) return; // Empty subset handling

    int size = r - l;
    int target_left = size / 2; // Strict bisection target
    
    // Update token to identify nodes in this recursive step
    subset_token++;
    for (int i = l; i < r; ++i) {
        subset_flag[perm[i]] = subset_token;
        side[perm[i]] = 1; // Initialize all to Right (1)
    }

    // BFS Initialization: Grow a connected region for Left (0) part
    // Pick a random start node in the current subset
    int start_node = perm[l + rand() % size];
    
    vector<int> q; 
    q.reserve(size);
    q.push_back(start_node);
    side[start_node] = 0; // Mark as Left
    
    int left_count = 1;
    int head = 0;
    
    // Grow Left set until target size is reached
    while (left_count < target_left) {
        if (head >= q.size()) {
            // If component is exhausted but target not reached, pick another unvisited node
            int next_node = -1;
            for (int i = l; i < r; ++i) {
                if (side[perm[i]] == 1) { // Node is still in Right
                    next_node = perm[i];
                    break;
                }
            }
            if (next_node == -1) break; // Should not happen
            side[next_node] = 0;
            q.push_back(next_node);
            left_count++;
            if (left_count >= target_left) break;
        }

        int u = q[head++];
        for (int v : adj[u]) {
            // Expand to neighbors that are in the subset and currently in Right
            if (subset_flag[v] == subset_token && side[v] == 1) {
                side[v] = 0;
                q.push_back(v);
                left_count++;
                if (left_count >= target_left) break;
            }
        }
    }

    // Refinement Phase: Batch FM-style swaps
    // We attempt to swap pairs of nodes (one from Left, one from Right) to reduce cut
    int passes = 8; // Number of refinement passes
    vector<pair<int, int>> candL, candR;
    candL.reserve(size);
    candR.reserve(size);

    for (int pass = 0; pass < passes; ++pass) {
        candL.clear();
        candR.clear();

        // Compute gains for all nodes in subset
        // Gain = (External Edges) - (Internal Edges)
        for (int i = l; i < r; ++i) {
            int u = perm[i];
            int g = 0;
            for (int v : adj[u]) {
                if (subset_flag[v] == subset_token) {
                    if (side[u] != side[v]) g++;
                    else g--;
                }
            }
            if (side[u] == 0) candL.push_back({g, u});
            else candR.push_back({g, u});
        }

        // Sort candidates by gain descending
        sort(candL.rbegin(), candL.rend());
        sort(candR.rbegin(), candR.rend());

        int limit = min(candL.size(), candR.size());
        int swaps = 0;
        
        // Greedily swap best pairs
        for (int i = 0; i < limit; ++i) {
            int u = candL[i].second;
            int v = candR[i].second;
            
            // Optimization: if sum of gains is non-positive, swap unlikely to help
            if (candL[i].first + candR[i].first <= 0) break;

            // Calculate actual gain accounting for edge between u and v
            int real_gain = candL[i].first + candR[i].first - (is_connected(u, v) ? 2 : 0);
            
            if (real_gain > 0) {
                side[u] = 1;
                side[v] = 0;
                swaps++;
            }
        }
        if (swaps == 0) break; // Stop if no improvement
    }

    // Reorder perm array: Left nodes [l, mid), Right nodes [mid, r)
    int mid = l;
    for (int i = l; i < r; ++i) {
        if (side[perm[i]] == 0) {
            swap(perm[i], perm[mid]);
            mid++;
        }
    }

    // Recursively solve for sub-parts
    solve(l, mid, k_sub / 2, base_id);
    solve(mid, r, k_sub / 2, base_id + k_sub / 2);
}

int main() {
    // Fixed seed for reproducibility
    srand(12345);
    
    read_input();
    
    // Initialize vectors
    p.resize(n);
    perm.resize(n);
    for(int i=0; i<n; ++i) perm[i] = i;
    side.resize(n);
    subset_flag.resize(n, 0);

    // Start recursive bisection
    solve(0, n, k_parts, 1);

    // Output results
    for (int i = 0; i < n; ++i) {
        printf("%d%c", p[i], (i == n - 1 ? '\n' : ' '));
    }

    return 0;
}
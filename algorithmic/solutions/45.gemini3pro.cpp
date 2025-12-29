/*
 * Problem: Balanced Graph Partitioning (DIMACS10-style)
 * Solution: Recursive Bisection with BFS-based initialization and FM-based refinement.
 * 
 * Time Complexity: O(M * log k * passes)
 * Space Complexity: O(N + M)
 */

#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <numeric>
#include <random>
#include <queue>

using namespace std;

// Global graph storage (Compressed Sparse Row format)
int n, m, k_parts;
double eps;
vector<int> xadj; // Indices into adj
vector<int> adj;  // Adjacency list

// Working arrays for the algorithm
vector<int> p;         // Permutation of nodes (tracks current subset mapping)
vector<int> loc;       // Local partition ID (0 or 1) for the current split
vector<int> mask;      // Visited mask to identify nodes involved in current recursion
vector<int> D;         // Gain values for refinement
vector<int> part_out;  // Final partition assignment
int mask_id = 0;       // Unique ID for current recursion level

// Read and process input
void read_input() {
    if (!(cin >> n >> m >> k_parts >> eps)) return;
    
    // Read edges temporarily into vector of vectors
    vector<vector<int>> raw_adj(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue; // Ignore self-loops
        raw_adj[u].push_back(v);
        raw_adj[v].push_back(u);
    }

    // Convert to CSR and remove duplicate edges
    xadj.resize(n + 2);
    adj.reserve(m * 2); 
    xadj[0] = 0;
    int current_idx = 0;

    for (int i = 1; i <= n; ++i) {
        sort(raw_adj[i].begin(), raw_adj[i].end());
        auto last = unique(raw_adj[i].begin(), raw_adj[i].end());
        raw_adj[i].erase(last, raw_adj[i].end());
        
        for (int v : raw_adj[i]) {
            adj.push_back(v);
        }
        current_idx += raw_adj[i].size();
        xadj[i] = current_idx;
    }
}

// Recursive Bisection Solver
void solve(int start_idx, int end_idx, int k_curr) {
    int num_nodes = end_idx - start_idx;
    if (num_nodes == 0) return;
    
    // Stop if we have reached the leaf level of recursion (k=1 means 1 part)
    if (k_curr == 1) return;

    // Strict bisection target size
    int target = num_nodes / 2;
    
    mask_id++;
    int cur_mask = mask_id;

    // Initialize all nodes in the current subset to '1' (right partition)
    for (int i = start_idx; i < end_idx; ++i) {
        mask[p[i]] = cur_mask;
        loc[p[i]] = 1; 
    }

    // --- 1. Initialization: BFS Growth ---
    // Select a random seed node
    static mt19937 rng(1337);
    int seed_idx = start_idx + rng() % num_nodes;
    int seed = p[seed_idx];
    
    queue<int> q;
    q.push(seed);
    loc[seed] = 0; // Assign seed to '0' (left partition)
    int count = 1;
    
    int scan_ptr = start_idx;
    
    // Grow region '0' until it reaches target size
    while (count < target) {
        if (q.empty()) {
            // Handle disconnected components by picking next unvisited node
            while (scan_ptr < end_idx && loc[p[scan_ptr]] == 0) {
                scan_ptr++;
            }
            if (scan_ptr >= end_idx) break; 
            int next_seed = p[scan_ptr];
            loc[next_seed] = 0;
            q.push(next_seed);
            count++;
        }
        
        if (count >= target) break;
        
        int u = q.front();
        q.pop();
        
        // Traverse neighbors
        for (int i = xadj[u]; i < xadj[u+1]; ++i) {
            int v = adj[i];
            // Only consider neighbors within the current subset
            if (mask[v] == cur_mask && loc[v] == 1) {
                loc[v] = 0;
                q.push(v);
                count++;
                if (count == target) break;
            }
        }
    }
    
    // --- 2. Refinement: Greedy Swaps (Batch FM) ---
    // Perform limited passes of swapping to improve cut size
    int passes = 4; 
    vector<int> left_set, right_set;
    left_set.reserve(target);
    right_set.reserve(num_nodes - target);

    for (int pass = 0; pass < passes; ++pass) {
        left_set.clear();
        right_set.clear();
        bool stable = true;

        // Compute gains for all nodes in subset
        // Gain = (edges to other side) - (edges to same side)
        for (int i = start_idx; i < end_idx; ++i) {
            int u = p[i];
            int my_side = loc[u];
            int d = 0;
            for (int idx = xadj[u]; idx < xadj[u+1]; ++idx) {
                int v = adj[idx];
                if (mask[v] == cur_mask) {
                    if (loc[v] != my_side) d++;
                    else d--;
                }
            }
            D[u] = d;
            if (my_side == 0) left_set.push_back(u);
            else right_set.push_back(u);
        }

        // Sort candidates by gain descending
        auto comp = [&](int a, int b) { return D[a] > D[b]; };
        sort(left_set.begin(), left_set.end(), comp);
        sort(right_set.begin(), right_set.end(), comp);
        
        // Try to swap pairs
        int lim = min((int)left_set.size(), (int)right_set.size());
        
        for (int i = 0; i < lim; ++i) {
            int u = left_set[i];
            int v = right_set[i];
            
            // Check if u and v are connected (penalizes swap)
            // Binary search is fast on sorted adjacency list
            bool connected = binary_search(adj.begin() + xadj[u], adj.begin() + xadj[u+1], v);
            
            // Calculate gain of swapping u and v
            int gain = D[u] + D[v] - 2 * (connected ? 1 : 0);
            
            if (gain > 0) {
                loc[u] = 1;
                loc[v] = 0;
                stable = false;
            } else {
                // Heuristic: stop if gain is too negative (sorted order implies degradation)
                if (D[u] + D[v] < -2) break; 
            }
        }
        if (stable) break;
    }
    
    // --- 3. Partition Array Reordering ---
    // Group nodes: '0' to the left, '1' to the right in the p array
    int left_ptr = start_idx;
    int right_ptr = end_idx - 1;
    while (left_ptr <= right_ptr) {
        while (left_ptr <= right_ptr && loc[p[left_ptr]] == 0) left_ptr++;
        while (left_ptr <= right_ptr && loc[p[right_ptr]] == 1) right_ptr--;
        if (left_ptr < right_ptr) {
            swap(p[left_ptr], p[right_ptr]);
            left_ptr++;
            right_ptr--;
        }
    }
    
    int mid = left_ptr; 
    
    // Recurse into subproblems
    solve(start_idx, mid, k_curr / 2);
    solve(mid, end_idx, k_curr / 2);
}

// Assign final 1..k partition IDs based on the implicit tree structure
void assign_parts(int start_idx, int end_idx, int k_curr, int part_base) {
    if (k_curr == 1) {
        for (int i = start_idx; i < end_idx; ++i) {
            part_out[p[i]] = part_base;
        }
        return;
    }
    int num_nodes = end_idx - start_idx;
    int mid = start_idx + num_nodes / 2;
    assign_parts(start_idx, mid, k_curr / 2, part_base);
    assign_parts(mid, end_idx, k_curr / 2, part_base + k_curr / 2);
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    read_input();

    if (n == 0) return 0;

    // Initialize arrays
    p.resize(n);
    iota(p.begin(), p.end(), 1); // Vertices 1..n
    loc.resize(n + 1);
    mask.resize(n + 1, 0);
    D.resize(n + 1);
    part_out.resize(n + 1);

    // Solve
    solve(0, n, k_parts);
    assign_parts(0, n, k_parts, 1);

    // Output results
    for (int i = 1; i <= n; ++i) {
        cout << part_out[i] << (i == n ? "" : " ");
    }
    cout << "\n";

    return 0;
}
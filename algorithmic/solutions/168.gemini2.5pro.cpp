#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>

// Using std namespace for competitive programming convenience
using namespace std;

// Type definitions for clarity
using ll = long long;

// Global variables for problem input
int N, M, H;
vector<ll> A;
vector<pair<int, int>> edges;
vector<vector<int>> G;

// Data structures to represent the forest state
vector<int> parent;
vector<vector<int>> children;
vector<int> height;
vector<int> root_of;

// Properties of each tree, indexed by the root vertex
vector<ll> sum_A;
vector<int> max_h;
vector<int> tree_size;

// Function to update the forest state after a merge operation.
// Merges the tree rooted at `u` to become a child of `p`.
// `r_p` is the root of the tree containing `p`.
void apply_merge(int u, int p, int r_p) {
    // 1. Find all nodes in the subtree rooted at `u` before the merge
    vector<int> subtree_nodes;
    queue<int> q_subtree;
    q_subtree.push(u);
    subtree_nodes.push_back(u);
    
    int head = 0;
    while(head < (int)subtree_nodes.size()) {
        int curr = subtree_nodes[head++];
        for (int child : children[curr]) {
            subtree_nodes.push_back(child);
        }
    }

    // 2. Update the root for all nodes in the merged subtree
    for (int node : subtree_nodes) {
        root_of[node] = r_p;
    }
    
    // 3. Update heights of all nodes in the merged subtree
    int new_max_h_in_subtree = 0;
    queue<pair<int, int>> q_height;
    q_height.push({u, height[p] + 1});

    while (!q_height.empty()) {
        auto [curr, h] = q_height.front();
        q_height.pop();
        height[curr] = h;
        new_max_h_in_subtree = max(new_max_h_in_subtree, h);
        for (int child : children[curr]) {
            q_height.push({child, h + 1});
        }
    }
    
    // 4. Update aggregate properties of the root of the new, larger tree
    sum_A[r_p] += sum_A[u];
    tree_size[r_p] += tree_size[u];
    max_h[r_p] = max(max_h[r_p], new_max_h_in_subtree);
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read input
    cin >> N >> M >> H;

    A.resize(N);
    G.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> A[i];
    }

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        edges.push_back({u, v});
        G[u].push_back(v);
        G[v].push_back(u);
    }
    
    // Vertex coordinates are not used in this greedy strategy
    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    // Initialize state: every node is a root of its own single-node tree
    parent.assign(N, -1);
    children.assign(N, vector<int>());
    height.assign(N, 0);
    root_of.resize(N);
    iota(root_of.begin(), root_of.end(), 0);

    sum_A = A;
    max_h.assign(N, 0);
    tree_size.assign(N, 1);

    // Greedily merge trees up to N-1 times
    for (int k = 0; k < N - 1; ++k) {
        double best_gain = 0;
        int r_to_merge = -1;
        int new_parent = -1;

        // Find the best possible merge in the current forest
        for (const auto& edge : edges) {
            int u = edge.first;
            int v = edge.second;

            int r_u = root_of[u];
            int r_v = root_of[v];

            if (r_u == r_v) continue;

            // Option 1: Try to merge tree of r_u into tree of r_v
            // by making root r_u a child of node v.
            if (height[v] + 1 + max_h[r_u] <= H) {
                double gain = (double)(height[v] + 1) * sum_A[r_u];
                if (gain > best_gain) {
                    best_gain = gain;
                    r_to_merge = r_u;
                    new_parent = v;
                }
            }

            // Option 2: Try to merge tree of r_v into tree of r_u
            // by making root r_v a child of node u.
            if (height[u] + 1 + max_h[r_v] <= H) {
                double gain = (double)(height[u] + 1) * sum_A[r_v];
                if (gain > best_gain) {
                    best_gain = gain;
                    r_to_merge = r_v;
                    new_parent = u;
                }
            }
        }

        if (r_to_merge == -1) {
            break; // No more valid merges found, stop.
        }

        // Perform the best merge found
        int r = r_to_merge;
        int p = new_parent;
        int r_p = root_of[p];

        parent[r] = p;
        children[p].push_back(r);
        
        apply_merge(r, p, r_p);
    }

    // Output the resulting parent array
    for (int i = 0; i < N; ++i) {
        cout << parent[i] << (i == N - 1 ? "" : " ");
    }
    cout << endl;

    return 0;
}
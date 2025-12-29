#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

struct Edge {
    int u, v, w;
};

int n;
vector<long long> depth;
vector<vector<int>> adj;
vector<int> sub_sz;
vector<int> parent;
vector<Edge> result_edges;

// Helper to query distance between two nodes
long long query_dist(int u, int v) {
    cout << "? " << u << " " << v << endl;
    long long d;
    cin >> d;
    return d;
}

// Update subtree sizes starting from u upwards to the root
void update_sz(int u) {
    int curr = u;
    while (curr != 0) {
        sub_sz[curr]++;
        curr = parent[curr];
    }
}

// Find the parent of node u in the current tree.
// We search within the subtree rooted at subtree_root.
// Returns the parent node index, or -1 if u is not in the subtree of subtree_root.
int find_parent(int u, int subtree_root) {
    int curr = subtree_root;
    
    // Construct the heavy path starting from curr
    int leaf = curr;
    int temp = curr;
    while (!adj[temp].empty()) {
        int heavy_child = -1;
        int max_sz = -1;
        for (int v : adj[temp]) {
            if (sub_sz[v] > max_sz) {
                max_sz = sub_sz[v];
                heavy_child = v;
            }
        }
        if (heavy_child != -1) {
            temp = heavy_child;
        } else {
            break;
        }
    }
    leaf = temp;
    
    // Query distance from u to the leaf of the heavy path
    long long d = query_dist(u, leaf);
    
    // Calculate the weighted depth of the LCA of u and leaf
    // formula: dist(u, leaf) = depth[u] + depth[leaf] - 2 * depth[lca]
    long long lca_depth_val = (depth[u] + depth[leaf] - d) / 2;
    
    // Identify the LCA node. It must be on the path from leaf to root.
    // We walk up from leaf until we find the node with the correct depth.
    int lca = leaf;
    while (lca != 0 && depth[lca] > lca_depth_val) {
        lca = parent[lca];
    }
    
    // If the identified LCA is strictly above curr, then u branches off 
    // before entering the subtree of curr. Thus u is not in this subtree.
    if (depth[lca] < depth[curr]) {
        return -1;
    }
    
    // If lca is exactly the leaf, then the leaf is the parent of u
    if (lca == leaf) return leaf;
    
    // Identify the child of lca that lies on the heavy path towards leaf
    int child_on_path = -1;
    int walker = leaf;
    while (walker != lca) {
        child_on_path = walker;
        walker = parent[walker];
    }
    
    // We know u is in the subtree of lca, but NOT in the subtree of child_on_path 
    // (otherwise the LCA would have been lower).
    // So u must be attached to lca directly or be in the subtree of one of the light children.
    
    vector<pair<int, int>> candidates;
    for (int child : adj[lca]) {
        if (child != child_on_path) {
            candidates.push_back({sub_sz[child], child});
        }
    }
    
    // If there are no other children, u must be attached to lca
    if (candidates.empty()) return lca;
    
    // Sort light children by size descending to optimize search
    sort(candidates.rbegin(), candidates.rend());
    
    for (auto& cand : candidates) {
        int res = find_parent(u, cand.second);
        if (res != -1) {
            return res;
        }
    }
    
    // If not found in any light child's subtree, the parent is lca
    return lca;
}

void solve() {
    cin >> n;
    if (n == 1) {
        cout << "! " << endl;
        return;
    }
    
    // Reset data structures
    depth.assign(n + 1, 0);
    adj.assign(n + 1, vector<int>());
    sub_sz.assign(n + 1, 0);
    parent.assign(n + 1, 0);
    result_edges.clear();
    
    // Determine depth of all nodes relative to node 1
    vector<pair<long long, int>> nodes;
    for (int i = 2; i <= n; ++i) {
        depth[i] = query_dist(1, i);
        nodes.push_back({depth[i], i});
    }
    
    // Sort nodes by depth so we build the tree top-down
    sort(nodes.begin(), nodes.end());
    
    // Initialize tree with root 1
    sub_sz[1] = 1;
    parent[1] = 0;
    
    // Insert nodes one by one
    for (auto& p : nodes) {
        int u = p.second;
        // Find parent of u in the current tree
        int p_u = find_parent(u, 1);
        
        // Update tree structure
        parent[u] = p_u;
        adj[p_u].push_back(u);
        sub_sz[u] = 1;
        update_sz(p_u);
        
        // Record edge
        result_edges.push_back({p_u, u, (int)(depth[u] - depth[p_u])});
    }
    
    // Output result
    cout << "!";
    for (const auto& e : result_edges) {
        cout << " " << e.u << " " << e.v << " " << e.w;
    }
    cout << endl;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int t;
    if (cin >> t) {
        while (t--) {
            solve();
        }
    }
    return 0;
}
#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to store node information for sorting
struct Node {
    int id;
    long long dist;
};

// Comparator to sort nodes by distance from the root
bool compareNodes(const Node& a, const Node& b) {
    return a.dist < b.dist;
}

int n;
vector<long long> dists;
vector<int> parent;
vector<vector<int>> children;
vector<int> sz;
vector<Node> sorted_nodes;

// Function to perform a query
long long query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    long long d;
    cin >> d;
    return d;
}

// Update subtree sizes after adding a new node
void update_size(int u) {
    while (u != -1) {
        sz[u]++;
        u = parent[u];
    }
}

// Trace up from v to find the ancestor at a specific depth
int get_ancestor_at_depth(int v, long long target_depth) {
    int curr = v;
    while (curr != -1) {
        if (dists[curr] == target_depth) return curr;
        // Since edge weights are at least 1, depth strictly decreases as we go up.
        // If we pass the target depth, the node is not on this path (should not happen with correct logic).
        if (dists[curr] < target_depth) break; 
        curr = parent[curr];
    }
    return -1;
}

void solve() {
    cin >> n;
    // Handle the case with a single node (no edges)
    if (n == 1) {
        cout << "! " << endl;
        return;
    }

    // Initialize distance array
    dists.assign(n + 1, 0);
    
    // Step 1: Query distances from root (node 1) to all other nodes
    // Node 1 is the root, so dist[1] = 0.
    for (int i = 2; i <= n; ++i) {
        dists[i] = query(1, i);
    }

    // Prepare nodes for sorting
    sorted_nodes.resize(n);
    for (int i = 1; i <= n; ++i) {
        sorted_nodes[i - 1] = {i, dists[i]};
    }

    // Step 2: Sort nodes by distance from root.
    // This ensures we add parents before children.
    sort(sorted_nodes.begin(), sorted_nodes.end(), compareNodes);

    // Step 3: Incrementally build the tree
    parent.assign(n + 1, -1);
    children.assign(n + 1, vector<int>());
    sz.assign(n + 1, 1);

    // The first node in sorted_nodes is the root (1).
    // We iterate starting from the second node.
    for (int i = 1; i < n; ++i) {
        int u = sorted_nodes[i].id;
        long long du = sorted_nodes[i].dist;

        int curr = 1; // Start searching for parent from the root
        vector<int> candidates = children[curr];

        while (true) {
            // If there are no candidate subtrees to check, u must be a child of curr
            if (candidates.empty()) {
                parent[u] = curr;
                children[curr].push_back(u);
                update_size(curr);
                break;
            }

            // Heuristic: Pick the 'heavy' child (largest subtree) to query first.
            // This mimics Heavy-Light Decomposition to minimize queries.
            int best_child = -1;
            int max_s = -1;
            int best_idx = -1;

            for (size_t k = 0; k < candidates.size(); ++k) {
                int c = candidates[k];
                if (sz[c] > max_s) {
                    max_s = sz[c];
                    best_child = c;
                    best_idx = k;
                }
            }

            // Find a leaf (or deep node) in the heavy child's subtree to use for the query.
            int v = best_child;
            while (!children[v].empty()) {
                int bc = -1;
                int ms = -1;
                for (int c : children[v]) {
                    if (sz[c] > ms) {
                        ms = sz[c];
                        bc = c;
                    }
                }
                v = bc;
            }

            // Query distance between u and v to find their LCA
            long long d_uv = query(u, v);
            // LCA distance formula: dist(lca) = (dist(u) + dist(v) - dist(u, v)) / 2
            long long d_lca = (du + dists[v] - d_uv) / 2;
            
            // Identify the LCA node in the current tree
            int lca = get_ancestor_at_depth(v, d_lca);

            if (lca == curr) {
                // If LCA is current node, u is NOT in the subtree of best_child.
                // We eliminate best_child from candidates and try other children of curr.
                candidates[best_idx] = candidates.back();
                candidates.pop_back();
            } else {
                // If LCA is deeper, u is in the subtree of lca.
                // Specifically, the path to u branches off at lca, so u is NOT in the 
                // child of lca that leads to v.
                
                // Identify which child of lca leads to v
                int child_towards_v = v;
                if (child_towards_v != lca) {
                    while (parent[child_towards_v] != lca) {
                        child_towards_v = parent[child_towards_v];
                    }
                } else {
                    // If lca == v, since v was a leaf in the current tree, u must be attached to v.
                    parent[u] = v;
                    children[v].push_back(u);
                    update_size(v);
                    break;
                }

                // Move our search to lca
                curr = lca;
                candidates = children[curr];
                
                // Remove the child that leads to v from candidates
                for (size_t k = 0; k < candidates.size(); ++k) {
                    if (candidates[k] == child_towards_v) {
                        candidates[k] = candidates.back();
                        candidates.pop_back();
                        break;
                    }
                }
            }
        }
    }

    // Output the answer
    cout << "!";
    for (int i = 2; i <= n; ++i) {
        long long w = dists[i] - dists[parent[i]];
        cout << " " << parent[i] << " " << i << " " << w;
    }
    cout << endl;
}

int main() {
    // Faster I/O
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
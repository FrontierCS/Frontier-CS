#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Function to perform an interactive query
long long query(int u, int v) {
    cout << "? " << u << " " << v << endl;
    long long d;
    cin >> d;
    return d;
}

const int MAXN = 100005;
long long dist_root[MAXN];
int parent_node[MAXN];
int sz[MAXN];
int heavy_child[MAXN]; // 0 if none
vector<int> children[MAXN];

struct Edge {
    int u, v;
    long long w;
};
vector<Edge> result_edges;

// Function to add a new node to the current tree
void add_node(int p, int u, long long w) {
    parent_node[u] = p;
    children[p].push_back(u);
    sz[u] = 1;
    heavy_child[u] = 0;
    
    result_edges.push_back({p, u, w});
    
    int curr = p;
    int child_node = u;
    // Update sizes and maintain heavy children pointers up to the root
    while (curr != 0) {
        sz[curr]++;
        if (heavy_child[curr] == 0) {
            heavy_child[curr] = child_node;
        } else {
            // Update heavy child if the modified subtree becomes larger
            if (heavy_child[curr] != child_node) {
                if (sz[child_node] > sz[heavy_child[curr]]) {
                    heavy_child[curr] = child_node;
                }
            }
        }
        child_node = curr;
        curr = parent_node[curr];
    }
}

// Get the leaf of the heavy path starting from u
int get_heavy_leaf(int u) {
    while (heavy_child[u] != 0) {
        u = heavy_child[u];
    }
    return u;
}

void solve() {
    int n;
    if (!(cin >> n)) return;
    
    result_edges.clear();
    // Reset data structures for the new test case
    for(int i=0; i<=n; ++i) {
        children[i].clear();
        sz[i] = 1;
        heavy_child[i] = 0;
        parent_node[i] = 0;
    }

    if (n == 1) {
        cout << "! " << endl;
        return;
    }

    dist_root[1] = 0;
    vector<pair<long long, int>> sorted_nodes;
    sorted_nodes.reserve(n-1);
    
    // Step 1: Query distances from root (node 1) to all other nodes
    for (int i = 2; i <= n; ++i) {
        dist_root[i] = query(1, i);
        sorted_nodes.push_back({dist_root[i], i});
    }
    
    // Step 2: Sort nodes by distance from root to process in increasing order of depth
    sort(sorted_nodes.begin(), sorted_nodes.end());
    
    // Step 3: Incrementally build the tree
    for (auto p : sorted_nodes) {
        int u = p.second;
        long long du = p.first;
        
        int curr = 1;
        int next_target = -1;
        long long next_dist = -1;
        
        while (true) {
            int v;
            long long d;
            
            // Determine target node to query in the current subtree
            if (next_target == -1) {
                v = get_heavy_leaf(curr);
                // If curr is a leaf, it must be the parent
                if (v == curr) {
                    add_node(curr, u, du - dist_root[curr]);
                    break;
                }
                d = query(u, v);
            } else {
                // Reuse query result if available from previous iteration
                v = next_target;
                d = next_dist;
                next_target = -1;
            }
            
            // Calculate depth of LCA(u, v)
            long long lca_depth = (du + dist_root[v] - d) / 2;
            
            // Find the node w on path curr...v that corresponds to this depth
            int w = v;
            int child_towards_v = 0;
            while (w != 0 && dist_root[w] > lca_depth) {
                child_towards_v = w;
                w = parent_node[w];
            }
            
            // If LCA is v, then v is the parent
            if (w == v) {
                add_node(v, u, du - dist_root[v]);
                break;
            }
            
            // Collect light children of w (excluding the heavy path we just checked)
            vector<pair<int, int>> candidates; 
            for (int c : children[w]) {
                if (c != child_towards_v) {
                    candidates.push_back({sz[c], c});
                }
            }
            
            // If no light children, w is the parent
            if (candidates.empty()) {
                add_node(w, u, du - dist_root[w]);
                break;
            }
            
            // Sort light children by size (heuristic)
            sort(candidates.rbegin(), candidates.rend());
            
            bool matched = false;
            for (auto cand : candidates) {
                int c = cand.second;
                int leaf_c = get_heavy_leaf(c);
                long long d2 = query(u, leaf_c);
                long long lca2_depth = (du + dist_root[leaf_c] - d2) / 2;
                
                // If LCA descends into c's subtree
                if (lca2_depth > dist_root[w]) {
                    curr = c;
                    next_target = leaf_c;
                    next_dist = d2;
                    matched = true;
                    break;
                }
            }
            
            if (!matched) {
                // u is not in any of the light children's subtrees
                add_node(w, u, du - dist_root[w]);
                break;
            }
        }
    }
    
    // Output the reconstructed edges
    cout << "!";
    for (const auto& e : result_edges) {
        cout << " " << e.u << " " << e.v << " " << e.w;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    if (cin >> t) {
        while(t--) {
            solve();
        }
    }
    return 0;
}
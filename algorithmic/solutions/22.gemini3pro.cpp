#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Maximum N as per constraints
const int MAXN = 100005;

int N;
vector<int> children[MAXN];
int L[MAXN], R[MAXN];

// Structure to represent a node in the new tree (a bag in tree decomposition)
struct Bag {
    vector<int> nodes;
    int id;
};

vector<Bag> bags;
vector<pair<int, int>> tree_edges;
int root_bag_idx[MAXN];

// Helper to create a new bag
int create_bag(const vector<int>& nodes) {
    Bag b;
    b.nodes = nodes;
    b.id = (int)bags.size() + 1;
    bags.push_back(b);
    return b.id;
}

// Helper to add an edge in the new tree
void add_edge(int u, int v) {
    tree_edges.push_back({u, v});
}

// First DFS: Compute L[u] and R[u]
// L[u] is the smallest index leaf in u's subtree (first in cycle order)
// R[u] is the largest index leaf in u's subtree (last in cycle order)
void dfs_LR(int u) {
    if (children[u].empty()) {
        L[u] = u;
        R[u] = u;
    } else {
        // Children are already sorted by index due to input processing loop
        dfs_LR(children[u][0]);
        L[u] = L[children[u][0]];
        
        for (size_t i = 1; i < children[u].size(); ++i) {
            dfs_LR(children[u][i]);
        }
        
        R[u] = R[children[u].back()];
    }
}

// Second DFS: Build the tree decomposition
void dfs_build(int u) {
    if (children[u].empty()) {
        // Leaf node: creates a single bag containing itself
        int id = create_bag({u});
        root_bag_idx[u] = id;
    } else {
        // Internal node
        int m = children[u].size();
        
        // Vectors to hold bag indices for this node's structure
        vector<int> H(m), S(m), Lnk(m > 1 ? m - 1 : 0);
        
        // Create H and S bags for each child
        for (int i = 0; i < m; ++i) {
            int c = children[u][i];
            // H_i covers the tree edge (u, c) and interfaces with child c
            // Bag: {u, c, L_c, R_c}
            H[i] = create_bag({u, c, L[c], R[c]});
            
            // S_i is part of the spine for node u, maintaining connectivity for u and R_u
            // Bag: {u, R_u, L_c, R_c}
            S[i] = create_bag({u, R[u], L[c], R[c]});
        }
        
        // Create Link bags to connect spine nodes and cover ring edges
        for (int i = 0; i < m - 1; ++i) {
            int c_curr = children[u][i];
            int c_next = children[u][i+1];
            // Lnk_i connects S_i and S_{i+1}, covers ring edge (R_c_curr, L_c_next)
            // Bag: {u, R_u, R_c_curr, L_c_next}
            Lnk[i] = create_bag({u, R[u], R[c_curr], L[c_next]});
        }
        
        // Connect the bags within u's structure
        for (int i = 0; i < m; ++i) {
            // Connect spine node S_i to handler H_i
            add_edge(S[i], H[i]);
            
            if (i < m - 1) {
                // Connect spine: S_i -- Lnk_i -- S_{i+1}
                add_edge(S[i], Lnk[i]);
                add_edge(Lnk[i], S[i+1]);
            }
        }
        
        // Recursively build children and connect them to H bags
        for (int i = 0; i < m; ++i) {
            int c = children[u][i];
            dfs_build(c);
            // Connect H_i to the root bag of child c
            add_edge(H[i], root_bag_idx[c]);
        }
        
        // The root bag for u exposed to its parent is S[0].
        // S[0] contains {u, R_u, L_c0, R_c0}. Since L_c0 == L_u, it has {u, L_u, R_u}.
        // This satisfies the parent's requirement.
        root_bag_idx[u] = S[0];
    }
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    // Read tree structure
    // Input format: N-1 lines. The i-th line (relative to these N-1 lines) contains p_i connecting p_i and i+1.
    // i ranges from 1 to N-1, corresponding to nodes 2 to N.
    for (int i = 2; i <= N; ++i) {
        int p;
        cin >> p;
        children[p].push_back(i);
    }

    // Process
    dfs_LR(1);
    dfs_build(1);

    // Output results
    cout << bags.size() << "\n";
    for (const auto& b : bags) {
        // Copy nodes to temp vector to sort and unique for valid set output
        vector<int> temp = b.nodes;
        sort(temp.begin(), temp.end());
        temp.erase(unique(temp.begin(), temp.end()), temp.end());
        
        cout << temp.size();
        for (int x : temp) {
            cout << " " << x;
        }
        cout << "\n";
    }

    for (const auto& e : tree_edges) {
        cout << e.first << " " << e.second << "\n";
    }

    return 0;
}
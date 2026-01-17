#include <bits/stdc++.h>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    cin >> N;

    vector<int> parent(N + 1, 0);
    vector<vector<int>> children(N + 1);
    for (int i = 2; i <= N; ++i) {
        int p;
        cin >> p;
        parent[i] = p;
        children[p].push_back(i);
    }

    // Determine leaves (nodes with no children)
    vector<bool> is_leaf(N + 1, false);
    for (int i = 1; i <= N; ++i) {
        if (children[i].empty()) {
            is_leaf[i] = true;
        }
    }

    // Collect leaves in increasing order
    vector<int> leaves;
    for (int i = 1; i <= N; ++i) {
        if (is_leaf[i]) {
            leaves.push_back(i);
        }
    }
    int L = leaves.size();

    // For each leaf, find its previous and next leaf in the cyclic order
    vector<int> leaf_idx(N + 1, -1);
    for (int i = 0; i < L; ++i) {
        leaf_idx[leaves[i]] = i;
    }

    // We will create one bag for each node except node 1.
    int K = N - 1;
    cout << K << "\n";

    // For each node u = 2..N, output its bag
    // Bag index of node u is u-1 (1-indexed bags)
    vector<vector<int>> bags(N);  // bags[u-1] for node u
    for (int u = 2; u <= N; ++u) {
        if (is_leaf[u]) {
            int idx = leaf_idx[u];
            int prev_leaf = leaves[(idx - 1 + L) % L];
            int next_leaf = leaves[(idx + 1) % L];
            set<int> bag_set;
            bag_set.insert(u);
            bag_set.insert(parent[u]);
            bag_set.insert(prev_leaf);
            bag_set.insert(next_leaf);
            bags[u-2].assign(bag_set.begin(), bag_set.end());
        } else {
            // internal node (not leaf)
            bags[u-2] = {u, parent[u]};
        }
    }

    // Output bags
    for (int i = 0; i < K; ++i) {
        cout << bags[i].size();
        for (int x : bags[i]) {
            cout << " " << x;
        }
        cout << "\n";
    }

    // Now output edges of the new tree
    vector<pair<int, int>> edges;
    // First, connect each non-root node to its parent (if parent is not root)
    for (int u = 2; u <= N; ++u) {
        int p = parent[u];
        if (p != 1) {
            edges.emplace_back(u-1, p-1);  // bag indices
        }
    }

    // Collect children of root (node 1)
    vector<int> root_children = children[1];
    // Sort to have deterministic order (not required but nice)
    sort(root_children.begin(), root_children.end());
    // Connect them in a path
    for (size_t i = 0; i + 1 < root_children.size(); ++i) {
        int u = root_children[i];
        int v = root_children[i+1];
        edges.emplace_back(u-1, v-1);
    }

    // Output edges
    for (auto& e : edges) {
        cout << e.first << " " << e.second << "\n";
    }

    return 0;
}
#include <iostream>
#include <vector>
#include <algorithm>
#include <set>

using namespace std;

const int MAXN = 100005;

int N;
vector<int> adj[MAXN];
vector<int> children[MAXN];
int L[MAXN], R[MAXN]; // Leftmost and rightmost leaf in subtree
bool is_leaf[MAXN];   // Leaf in the original tree sense

struct Bag {
    vector<int> nodes;
    int id;
};

vector<Bag> bags;
vector<pair<int, int>> tree_edges;

// Creates a bag with given nodes, sorts and unique them, assigns ID
int create_bag(vector<int> nodes) {
    sort(nodes.begin(), nodes.end());
    nodes.erase(unique(nodes.begin(), nodes.end()), nodes.end());
    Bag b;
    b.nodes = nodes;
    b.id = bags.size() + 1;
    bags.push_back(b);
    return b.id;
}

void add_edge(int u, int v) {
    tree_edges.push_back({u, v});
}

// Returns the ID of the bag representing the subtree rooted at u
// The returned bag is guaranteed to contain {u, L[u], R[u]}
// This allows the parent to connect and maintain connectivity of u, L[u], R[u]
// and cover the cycle edge passing through L[u] and R[u] (specifically R[u]-nextL and prevR-L[u])
int solve(int u) {
    if (is_leaf[u]) {
        // For a leaf, L[u] = R[u] = u. Bag {u} is sufficient.
        return create_bag({u});
    }

    int m = children[u].size();
    vector<int> child_bag_ids;
    for (int v : children[u]) {
        child_bag_ids.push_back(solve(v));
    }

    // Process first child
    int c1 = children[u][0];
    // This bag covers edge (u, c1) and starts the chain
    // Must contain u, c1, L[c1], R[c1]
    int ret1_id = create_bag({u, c1, L[c1], R[c1]});
    add_edge(ret1_id, child_bag_ids[0]);

    int curr_bag_id = ret1_id;
    int curr_R = R[c1]; // The rightmost leaf of the processed part

    // Process remaining children
    for (int i = 1; i < m; ++i) {
        int ci = children[u][i];
        int l_next = L[ci];
        int r_next = R[ci];

        // I bag: connects the previous part to the current child's left leaf
        // Covers the cycle edge (curr_R, l_next)
        // Must contain u (for continuity), L[u] (to be passed to end), curr_R, l_next
        int I_id = create_bag({u, L[u], curr_R, l_next});
        add_edge(curr_bag_id, I_id);

        // ret' bag: acts as the attachment point for the child's subtree
        // Covers edge (u, ci)
        // Must contain u, ci, l_next, r_next
        // We connect this to child's returned bag which has {ci, l_next, r_next}
        int ret_prime_id = create_bag({u, ci, l_next, r_next});
        add_edge(ret_prime_id, child_bag_ids[i]);

        // J bag: bridges I and ret', and prepares for next step
        // Must contain u, L[u], l_next, r_next
        // Connects to I (share u, L[u], l_next)
        // Connects to ret' (share u, l_next, r_next)
        int J_id = create_bag({u, L[u], l_next, r_next});
        add_edge(I_id, J_id);
        add_edge(J_id, ret_prime_id);

        curr_bag_id = J_id;
        curr_R = r_next;
    }

    // The final bag curr_bag_id contains {u, L[u], R[u]}
    // because L[u] was carried through, and curr_R is updated to R[last_child] = R[u]
    return curr_bag_id;
}

void dfs_pre(int u, int p) {
    // Collect children
    for (int v : adj[u]) {
        if (v != p) {
            children[u].push_back(v);
        }
    }
    // Sort children by index to match planar embedding / pre-order property
    sort(children[u].begin(), children[u].end());

    if (children[u].empty()) {
        is_leaf[u] = true;
        L[u] = u;
        R[u] = u;
    } else {
        is_leaf[u] = false;
        for (int v : children[u]) {
            dfs_pre(v, u);
        }
        L[u] = L[children[u][0]];
        R[u] = R[children[u].back()];
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;

    for (int i = 1; i < N; ++i) {
        int p;
        cin >> p;
        // Edge between p and i+1
        adj[p].push_back(i + 1);
        adj[i + 1].push_back(p);
    }

    dfs_pre(1, 0);
    solve(1);

    cout << bags.size() << "\n";
    for (const auto& b : bags) {
        cout << b.nodes.size();
        for (int x : b.nodes) {
            cout << " " << x;
        }
        cout << "\n";
    }
    for (const auto& e : tree_edges) {
        cout << e.first << " " << e.second << "\n";
    }

    return 0;
}
#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

using namespace std;

int n;

// Query: is v in Steiner(S)?
// S is passed as a vector.
// Returns 1 if yes, 0 if no.
int query(int v, const vector<int>& S) {
    if (S.empty()) return 0;
    cout << "? " << S.size() << " " << v;
    for (int x : S) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    if (res == -1) exit(0);
    return res;
}

// Check if u is ancestor of v (assuming 1 is root)
// Equivalent to: u is on path between 1 and v
// Query: ? 2 u 1 v
bool is_ancestor(int u, int v) {
    if (u == v) return true;
    if (u == 1) return true;
    if (v == 1) return false;
    // query ? 2 u 1 v
    return query(u, {1, v});
}

// Check if u is ancestor of ANY node in S
// Equivalent to checking if u is in Steiner({1} U S)
bool is_ancestor_of_any(int u, const vector<int>& S) {
    if (S.empty()) return false;
    vector<int> args = S;
    args.push_back(1);
    return query(u, args);
}

struct Node {
    int id;
    int size; // Subtree size in the reconstructed tree
    vector<int> children;
};

Node nodes[1005];
bool is_leaf_flag[1005];

// Full size update from scratch
int recalc_size(int u) {
    int s = 1;
    for (int c : nodes[u].children) {
        s += recalc_size(c);
    }
    nodes[u].size = s;
    return s;
}

void insert_node(int u, bool is_internal) {
    // Start at root = 1
    int curr = 1;
    nodes[u].children.clear();
    nodes[u].size = 1;

    while (true) {
        // Identify candidate children to descend
        vector<int> candidates;
        if (is_internal) {
            // If u is internal, it can descend into any child
            candidates = nodes[curr].children;
        } else {
            // If u is leaf, it can only descend into internal children
            for (int c : nodes[curr].children) {
                if (!is_leaf_flag[c]) {
                    candidates.push_back(c);
                }
            }
        }

        // Sort candidates by size descending to optimize heavy path traversal
        sort(candidates.begin(), candidates.end(), [](int a, int b) {
            return nodes[a].size > nodes[b].size;
        });

        int next_node = -1;
        for (int c : candidates) {
            if (is_ancestor(c, u)) {
                next_node = c;
                break;
            }
        }

        if (next_node != -1) {
            curr = next_node;
        } else {
            // Attach u to curr
            // If u is internal, it might become parent of some existing children of curr
            // If u is leaf, it cannot be parent of existing nodes (as we insert leaves last).
            if (is_internal) {
                vector<int> moved;
                // Check if u is ancestor of any current children of curr
                // We use batch query for efficiency
                if (!nodes[curr].children.empty()) {
                    if (is_ancestor_of_any(u, nodes[curr].children)) {
                        vector<int> kept;
                        for (int c : nodes[curr].children) {
                            if (is_ancestor(u, c)) {
                                moved.push_back(c);
                            } else {
                                kept.push_back(c);
                            }
                        }
                        nodes[curr].children = kept;
                    }
                }
                nodes[u].children = moved;
            }
            
            nodes[curr].children.push_back(u);
            break;
        }
    }
    // Update sizes
    recalc_size(1);
}

int main() {
    ios_base::sync_with_stdio(false); // Does not affect interactive IO if flush is used
    cin >> n;
    if (n == 1) {
        cout << "!" << endl;
        return 0;
    }

    // Identify leaves. Node 1 is treated as root/internal.
    is_leaf_flag[1] = false;
    for (int i = 2; i <= n; ++i) {
        vector<int> others;
        for (int j = 1; j <= n; ++j) {
            if (i == j) continue;
            others.push_back(j);
        }
        // If i is a leaf, it is not on the Steiner tree of V \ {i}.
        if (query(i, others) == 0) {
            is_leaf_flag[i] = true;
        } else {
            is_leaf_flag[i] = false;
        }
    }

    vector<int> internals;
    vector<int> leaves;
    for (int i = 2; i <= n; ++i) {
        if (is_leaf_flag[i]) leaves.push_back(i);
        else internals.push_back(i);
    }

    // Initialize root
    nodes[1].id = 1;
    nodes[1].size = 1;

    // Shuffle and insert internals first
    mt19937 rng(1337);
    shuffle(internals.begin(), internals.end(), rng);
    for (int u : internals) {
        insert_node(u, true);
    }

    // Shuffle and insert leaves
    shuffle(leaves.begin(), leaves.end(), rng);
    for (int u : leaves) {
        insert_node(u, false);
    }

    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int c : nodes[i].children) {
            cout << i << " " << c << endl;
        }
    }
    cout << flush;

    return 0;
}
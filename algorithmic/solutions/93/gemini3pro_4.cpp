#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <random>

using namespace std;

// Global variables
int n;

// Function to perform a query to the black box
// Returns the size of the greedy set
int query(const vector<int>& vec) {
    if (vec.empty()) return 0;
    cout << "? " << vec.size();
    for (int x : vec) {
        cout << " " << x;
    }
    cout << endl;
    int res;
    cin >> res;
    return res;
}

struct Node {
    int id;
    int parent = 0;
    vector<int> children;
    int size = 1;
    int heavy_child = 0;
};

vector<Node> nodes;

// Update subtree size and heavy child pointers moving up from u
void update_up(int u) {
    while (u != 0) {
        nodes[u].size++;
        int p = nodes[u].parent;
        if (p != 0) {
            int hc = nodes[p].heavy_child;
            if (hc == 0 || nodes[u].size > nodes[hc].size) {
                nodes[p].heavy_child = u;
            }
        }
        u = p;
    }
}

int main() {
    // Optimize I/O operations (though interactive requires flushing)
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int ty;
    if (!(cin >> n >> ty)) return 0;

    nodes.resize(n + 1);
    for (int i = 1; i <= n; ++i) nodes[i].id = i;

    // Generate random permutation for topological sort heuristic
    vector<int> p(n);
    iota(p.begin(), p.end(), 1);
    mt19937 rng(1337);
    shuffle(p.begin(), p.end(), rng);

    // Compute val(u) for each node to determine insertion order
    // val(u) roughly correlates with depth/position in tree
    vector<pair<int, int>> sorted_nodes(n);
    for (int i = 1; i <= n; ++i) {
        vector<int> q_vec;
        q_vec.reserve(n);
        q_vec.push_back(i);
        for (int x : p) {
            if (x != i) q_vec.push_back(x);
        }
        int val = query(q_vec);
        sorted_nodes[i - 1] = {val, i};
    }

    sort(sorted_nodes.begin(), sorted_nodes.end());

    // The node with the smallest val is the root
    int root = sorted_nodes[0].second;
    nodes[root].parent = 0;

    // Incrementally build the tree
    for (int i = 1; i < n; ++i) {
        int u = sorted_nodes[i].second;
        int curr = root;
        
        while (true) {
            // 1. Try to descend via heavy chain
            vector<int> chain;
            int temp = curr;
            while (nodes[temp].heavy_child != 0) {
                temp = nodes[temp].heavy_child;
                chain.push_back(temp);
            }

            if (!chain.empty()) {
                int tail = chain.back();
                // Check if the tail of the heavy chain is an ancestor of u
                // Query: {tail, u}. If 1 -> tail is ancestor (or u is ancestor, but order guarantees tail is above)
                int res = query({tail, u});
                if (res == 1) {
                    // Tail is ancestor, jump directly to tail
                    curr = tail;
                } else {
                    // Tail is not ancestor. The split point is somewhere on the chain.
                    // Binary search to find the deepest ancestor on the chain.
                    int low = 0, high = chain.size() - 1;
                    int last_idx = -1;
                    while (low <= high) {
                        int mid = low + (high - low) / 2;
                        if (query({chain[mid], u}) == 1) {
                            last_idx = mid;
                            low = mid + 1;
                        } else {
                            high = mid - 1;
                        }
                    }
                    if (last_idx != -1) {
                        curr = chain[last_idx];
                    }
                    // If last_idx == -1, curr remains the parent of the chain head, which is correct.
                }
            }
            
            // Now curr is the deepest ancestor found on the heavy path.
            // u must be in a light subtree of curr, or u is a new child of curr.
            
            // Gather candidate children (all children except the heavy child)
            // We know the heavy child is NOT an ancestor (otherwise we would have descended into it/past it)
            // Exception: if we stopped at 'tail' and tail had no heavy child, hc is 0, so we check all.
            vector<int> candidates;
            int hc = nodes[curr].heavy_child;
            for (int child : nodes[curr].children) {
                if (child != hc) {
                    candidates.push_back(child);
                }
            }
            
            if (candidates.empty()) {
                // No light children to check, so u is a direct child of curr
                nodes[u].parent = curr;
                nodes[curr].children.push_back(u);
                update_up(u);
                break;
            }
            
            // Check if any light child is an ancestor of u using a group query
            vector<int> q_cand;
            q_cand.reserve(candidates.size() + 1);
            q_cand.push_back(u);
            q_cand.insert(q_cand.end(), candidates.begin(), candidates.end());
            
            int res = query(q_cand);
            if (res == 1 + (int)candidates.size()) {
                // None of the candidates is an ancestor
                nodes[u].parent = curr;
                nodes[curr].children.push_back(u);
                update_up(u);
                break;
            } else {
                // Exactly one candidate is an ancestor. Find it via binary search.
                int low = 0, high = candidates.size() - 1;
                while (low < high) {
                    int mid = low + (high - low) / 2;
                    // Check left half
                    vector<int> sub;
                    sub.reserve(mid - low + 2);
                    sub.push_back(u);
                    for (int k = low; k <= mid; ++k) sub.push_back(candidates[k]);
                    
                    int expected = 1 + (mid - low + 1);
                    int r = query(sub);
                    if (r < expected) {
                        // Ancestor is in the left half (something was blocked)
                        high = mid;
                    } else {
                        // Ancestor is in the right half
                        low = mid + 1;
                    }
                }
                curr = candidates[low];
            }
        }
    }

    // Output result
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << nodes[i].parent;
    }
    cout << endl;

    return 0;
}
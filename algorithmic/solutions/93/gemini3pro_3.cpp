#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>

using namespace std;

int N;
int parent[3005];
vector<int> adj[3005];
int sub_sz[3005];
int heavy[3005];

// Wrapper for the interactive query
int query(const vector<int>& v) {
    cout << "? " << v.size();
    for (int x : v) cout << " " << x;
    cout << endl;
    int res;
    cin >> res;
    return res;
}

// Update subtree size and heavy child for a node
void update_size(int u) {
    sub_sz[u] = 1;
    heavy[u] = 0;
    int max_s = -1;
    for (int c : adj[u]) {
        if (sub_sz[c] > max_s) {
            max_s = sub_sz[c];
            heavy[u] = c;
        }
        sub_sz[u] += sub_sz[c];
    }
}

// Update properties on the path from u to root
void update_path(int u) {
    while (u != 0) {
        update_size(u);
        u = parent[u];
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int ty;
    if (!(cin >> N >> ty)) return 0;

    // Create a random permutation for consistent depth estimation
    vector<int> p(N);
    iota(p.begin(), p.end(), 1);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    shuffle(p.begin(), p.end(), rng);

    // Initial query for each node to estimate topological order
    // D[u] = Q(u, P \ {u}). Larger value -> fewer skipped -> deeper/smaller subtree.
    // Actually, smaller result -> more skipped -> more related -> higher up (closer to root).
    // result = 1 + |unrelated|.
    // |related| = (N-1) - (result-1) = N - result.
    // Higher |related| implies u is an ancestor of more nodes.
    // So smaller result -> u is higher.
    vector<pair<int, int>> nodes(N);
    for (int i = 1; i <= N; ++i) {
        vector<int> q;
        q.reserve(N);
        q.push_back(i);
        for (int x : p) {
            if (x != i) q.push_back(x);
        }
        int res = query(q);
        nodes[i - 1] = {res, i};
    }

    // Sort nodes: Root will be at index 0
    sort(nodes.begin(), nodes.end());

    int root = nodes[0].second;
    parent[root] = 0;
    sub_sz[root] = 1;
    heavy[root] = 0;

    // Insert nodes one by one
    for (int i = 1; i < N; ++i) {
        int u = nodes[i].second;
        int curr = root;
        
        // Traverse down to find parent
        while (true) {
            // Build the heavy chain starting from curr
            vector<int> chain;
            int temp = curr;
            while (temp != 0) {
                chain.push_back(temp);
                temp = heavy[temp];
            }
            
            // Binary search on the heavy chain to find the deepest ancestor of u
            int l = 0, r = chain.size() - 1;
            int deepest_idx = 0; // curr is always an ancestor
            
            // Optimization: if chain size is 1, no need to query
            if (chain.size() > 1) {
                l = 1; // start checking from next
                while (l <= r) {
                    int mid = l + (r - l) / 2;
                    // Check if chain[mid] is an ancestor of u
                    // u is not in the tree yet (conceptually), but we check relation.
                    // If related, since u is deeper (by sorting order), chain[mid] must be anc.
                    vector<int> q = {u, chain[mid]};
                    int res = query(q);
                    if (res == 1) {
                        deepest_idx = mid;
                        l = mid + 1;
                    } else {
                        r = mid - 1;
                    }
                }
            }
            
            curr = chain[deepest_idx];
            
            // Collect light children
            vector<int> light_children;
            for (int c : adj[curr]) {
                if (c != heavy[curr]) {
                    light_children.push_back(c);
                }
            }
            
            if (light_children.empty()) {
                // No light children, u must be a new child of curr
                parent[u] = curr;
                adj[curr].push_back(u);
                update_path(curr);
                break;
            }
            
            // Find if u belongs to any light child's subtree
            int found_child = -1;
            int lc_l = 0, lc_r = light_children.size() - 1;
            bool confirmed_in_range = false;

            while (lc_l <= lc_r) {
                if (lc_l == lc_r) {
                    if (confirmed_in_range) {
                        found_child = light_children[lc_l];
                    } else {
                        vector<int> q = {u, light_children[lc_l]};
                        if (query(q) == 1) found_child = light_children[lc_l];
                    }
                    break;
                }
                
                int mid = lc_l + (lc_r - lc_l) / 2;
                vector<int> q;
                q.reserve(mid - lc_l + 2);
                q.push_back(u);
                for (int k = lc_l; k <= mid; ++k) q.push_back(light_children[k]);
                
                int res = query(q);
                int expected_if_none = (mid - lc_l + 1) + 1;
                // If result < expected, one child was related (and thus skipped)
                if (res < expected_if_none) {
                    // It is in the left half
                    lc_r = mid;
                    confirmed_in_range = true;
                } else {
                    // It is not in the left half
                    lc_l = mid + 1;
                    // confirmed_in_range status persists for the right half 
                    // (if it was confirmed in [L, R] and not in Left, must be in Right)
                }
            }
            
            if (found_child != -1) {
                curr = found_child;
            } else {
                // Not related to any child, so it's a direct child of curr
                parent[u] = curr;
                adj[curr].push_back(u);
                update_path(curr);
                break;
            }
        }
    }

    cout << "!";
    for (int i = 1; i <= N; ++i) {
        cout << " " << parent[i];
    }
    cout << endl;

    return 0;
}
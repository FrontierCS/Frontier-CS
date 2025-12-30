#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

int n;
vector<long long> dists;
vector<int> p_node;
vector<vector<int>> adj;
vector<int> sub_sz;
map<pair<int,int>, long long> memo;

long long query(int u, int v) {
    if (u == v) return 0;
    if (u > v) swap(u, v);
    if (memo.count({u, v})) return memo[{u, v}];
    cout << "? " << u << " " << v << endl;
    long long d;
    cin >> d;
    return memo[{u, v}] = d;
}

int get_heavy_leaf(int u) {
    while (!adj[u].empty()) {
        int best = -1, max_s = -1;
        for (int c : adj[u]) {
            if (sub_sz[c] > max_s) {
                max_s = sub_sz[c];
                best = c;
            }
        }
        u = best;
    }
    return u;
}

int get_ancestor_at_depth(int u, long long d) {
    while (u != 0 && dists[u] > d) {
        u = p_node[u];
    }
    return u;
}

void solve() {
    if (!(cin >> n)) return;
    
    memo.clear();
    
    if (n == 1) {
        cout << "! " << endl;
        return;
    }

    dists.assign(n + 1, 0);
    for (int i = 2; i <= n; ++i) {
        dists[i] = query(1, i);
    }

    vector<int> nodes(n - 1);
    for (int i = 0; i < n - 1; ++i) nodes[i] = i + 2;
    sort(nodes.begin(), nodes.end(), [&](int a, int b) {
        return dists[a] < dists[b];
    });

    p_node.assign(n + 1, 0);
    adj.assign(n + 1, vector<int>());
    sub_sz.assign(n + 1, 1);
    
    // Incrementally insert nodes
    for (int u : nodes) {
        int curr = 1;
        while (true) {
            if (adj[curr].empty()) {
                p_node[u] = curr;
                adj[curr].push_back(u);
                int tmp = u;
                while (tmp != 0) {
                    sub_sz[tmp]++;
                    tmp = p_node[tmp];
                }
                break;
            }
            
            // Identify heavy child
            int heavy_child = -1, max_s = -1;
            for (int c : adj[curr]) {
                if (sub_sz[c] > max_s) {
                    max_s = sub_sz[c];
                    heavy_child = c;
                }
            }
            
            // Query against a leaf in the heavy subtree
            int v = get_heavy_leaf(heavy_child);
            long long d_uv = query(u, v);
            long long lca_d = (dists[u] + dists[v] - d_uv) / 2;
            
            int w = get_ancestor_at_depth(v, lca_d);
            
            if (w != curr) {
                curr = w;
                // w is a descendant of curr, so we moved down the heavy path.
                // We know u branches off at w, and u is NOT in the child of w that leads to v.
            }
            
            // Identify the child of curr that leads to v (to exclude it)
            int child_towards_v = -1;
            int tmp = v;
            while (p_node[tmp] != curr) {
                tmp = p_node[tmp];
            }
            child_towards_v = tmp;
            
            // Check other children (candidates)
            vector<int> candidates;
            for (int c : adj[curr]) {
                if (c != child_towards_v) candidates.push_back(c);
            }
            // Sort by size to check larger subtrees first (heuristic)
            sort(candidates.begin(), candidates.end(), [&](int a, int b){
                return sub_sz[a] > sub_sz[b];
            });
            
            bool found = false;
            for (int c : candidates) {
                int v_prime = get_heavy_leaf(c);
                long long d_uv_p = query(u, v_prime);
                long long lca_d_p = (dists[u] + dists[v_prime] - d_uv_p) / 2;
                
                if (lca_d_p > dists[curr]) {
                    // LCA is inside c's subtree
                    curr = get_ancestor_at_depth(v_prime, lca_d_p);
                    found = true;
                    break;
                }
            }
            
            if (found) continue;
            
            // If not in any existing child's subtree, attach to curr
            p_node[u] = curr;
            adj[curr].push_back(u);
            tmp = u;
            while (tmp != 0) {
                sub_sz[tmp]++;
                tmp = p_node[tmp];
            }
            break;
        }
    }
    
    cout << "!";
    for (int i = 2; i <= n; ++i) {
        cout << " " << p_node[i] << " " << i << " " << (dists[i] - dists[p_node[i]]);
    }
    cout << endl;
}

int main() {
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